import json
import logging
import sys
import threading
import platform

# Monkey patch json encoder. We disable the type system here as monkey patching is...weird
from json import JSONEncoder

def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj) # type: ignore

_default.default = JSONEncoder().default # type:ignore
JSONEncoder.default = _default # type: ignore



from dotenv import dotenv_values
from flask import Flask, flash, get_flashed_messages, redirect, request, url_for
from flask_inertia import Inertia, render_inertia
from flask_principal import Principal, identity_changed, Identity
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_vite import Vite
from typing import cast

from .auth import AuthManager, User, admin_permissions
from .contract_endpoints import contract_endpoints
from .contract_endpoints.blueprint import get_outstanding_contracts
from .contract_endpoints.fetcher import pull_contracts
from .contract_endpoints.typing import BaseID, CorpID
from .data import DataSource
from .ValkeyInformationProvider import ValkeyInformationProvider
from .data.esi import ESI
from .filters import filters_endpoints
from .data.esi.auth import decode_token

SECRET_KEY = "AFHFCHDSJCAS"
INERTIA_TEMPLATE = "index.html"

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler(sys.stdout))

app = Flask(__name__, static_folder="static")

app.config.from_object(__name__)
login_manager = LoginManager(app)
Vite(app)
principal = Principal(app)
inertia = Inertia(app)

app.register_blueprint(contract_endpoints, url_prefix="/fuel")

if platform.system() == "Windows":
    app.config.update({"VITE_NPM_BIN_PATH": "npm.ps1"})

if app.config["DEBUG"]:
    from flask_cors import CORS
    CORS(app)
    app.config["CORS_HEADERS"] = "Content-Type"

config = dotenv_values(".env.development" if app.config["DEBUG"] else ".env")
if not config["CLIENT_ID"] or not config["CLIENT_SECRET"]:
    sys.exit("Missing client ID or client secret, cannot start")

valkey_host = config.get("VALKEY_HOST", "localhost")
if not valkey_host:
    sys.exit("No given valkey host, cannot start")
user_auth = AuthManager(host=valkey_host if valkey_host else "localhost")

provider = ValkeyInformationProvider(app, valkey_host)
datasource: DataSource = ESI(config["CLIENT_ID"], config["CLIENT_SECRET"])

if "vite" not in sys.argv:
    if "CORP_ID" not in config:
        sys.exit("Missing corp id, cannot start")
    _id = config["CORP_ID"]
    if _id is None:
        sys.exit("Corp ID was set to None, cannot start")

    corp_id = CorpID(BaseID(int(_id)))
    contract_endpoints.corp_id = corp_id
    contract_endpoints.create_valkey_client(valkey_host if valkey_host else "localhost")
    filters_endpoints.create_valkey_client(valkey_host if valkey_host else "localhost")
    contracting_thread = threading.Thread(
        target=pull_contracts,
        name="Puller Thread",
        args=(datasource, corp_id, valkey_host),
        daemon=True,
    )

    contracting_thread.start()

# Inertia helpers
def get_current_user():
    return json.dumps(current_user.__dict__)

def get_messages():
    return json.dumps(get_flashed_messages(with_categories=True))

def get_is_admin():
    return admin_permissions.can()

# Shared data
inertia.share("client_id", config["CLIENT_ID"])
inertia.share("scopes", config["SCOPES"])
inertia.share("redirect_uri", config["REDIRECT_URI"])
inertia.share("current_user", get_current_user)
inertia.share("messages", get_messages)
inertia.share("is_admin", get_is_admin)


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect("/contracts")  # Default to the contracts page

    return render_inertia("Home")


@app.route("/login")
def login_endpoint():
    login_code = request.args.get("code")
    if not login_code:
        flash("ESI did not return a auth code", "error")
        return redirect("/")

    response = datasource.get_tokens(login_code)

    token_data: dict[str, str] = decode_token(response.access_token)
    character_id: str = token_data["sub"].split(":")[2]

    corp_id = datasource.get_character_corp(character_id)
    if config["CORP_ID"] and corp_id != int(config["CORP_ID"]):
        flash(f"{token_data["name"]} is not in the necessary corp", "warning")
        app.logger.warning(f"Character {token_data['name']} attempted to log in")
        return redirect("/")

    assert response.refresh_token

    user_auth.save_user(
        int(character_id),
        response.access_token,
        response.refresh_token,
        response.expiry,
        token_data["name"],
    )

    login_user(User(character_id, token_data["name"]))
    identity_changed.send(app, identity=Identity(int(character_id)))
    return redirect("/")


@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")


@login_manager.user_loader
def load_user(user_id):
    return user_auth.get_user(user_id)


@app.route("/contracts")
@login_required
def contracts():
    def get_contracts():
        return get_outstanding_contracts(corp_id)

    props = {"contracts": get_contracts}
    return render_inertia("Contracts", props)


@app.route("/fuelling")
@login_required
def fuelling():
    return render_inertia("Fuelling")


@app.route("/admin")
@login_required
@admin_permissions.require(http_exception=403)
def admin():
    props = {}
    if valkey_host:
        import valkey
        valkey_client = valkey.Valkey(host=valkey_host)

        filters : set[bytes] = cast(set[bytes], valkey_client.smembers("filters"))

        if filters:
            props.update({
                "filters": [json.loads(x.decode()) for x in filters]
            })

    return render_inertia("Admin", props=props)

app.register_blueprint(filters_endpoints, url_prefix="/admin/filters")
