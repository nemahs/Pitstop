import json
import logging
import sys

sys.path += "."
import threading
import platform
from types import SimpleNamespace
from typing import cast, Any
from dotenv import dotenv_values
from flask import Flask, flash, get_flashed_messages, redirect, request
from flask_inertia import Inertia, render_inertia
from flask_principal import Principal, identity_changed, Identity
from flask_cors import CORS
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_vite import Vite
import sqlalchemy as sa
from werkzeug.middleware.proxy_fix import ProxyFix
from valkey import Valkey

from .auth import AuthManager, User, admin_permissions
from .contract_endpoints import create_contract_blueprint, pull_contracts, CorpID, BaseID, get_outstanding_contracts
from .contract_endpoints.fetcher import get_key
from .ValkeyInformationProvider import ValkeyInformationProvider
from .data.esi import ESI
from .data.esi.corporation import open_corp_contract
from .filters import create_filter_endpoints
from .data.esi.auth import decode_token

SECRET_KEY = "AFHFCHDSJCAS"
INERTIA_TEMPLATE = "index.html"

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler(sys.stdout))

# region Flask setup

app = Flask(__name__, static_folder="static")
if platform.system() == "Windows":
    app.config.update({"VITE_NPM_BIN_PATH": "npm.cmd"})

app.config.from_object(__name__)

login_manager = LoginManager(app)
Vite(app)
principal = Principal(app)
inertia = Inertia(app)


def register_blueprints(app: Flask, valkey_client: Valkey, esi: ESI):
    contract_endpoints = create_contract_blueprint(corp_id, valkey_host, esi, engine)
    app.register_blueprint(contract_endpoints, url_prefix="/fuel")

    filter_endpoints = create_filter_endpoints(valkey_client)

    @filter_endpoints.before_request
    @admin_permissions.require()
    def pre_filters():
        pass

    app.register_blueprint(filter_endpoints, url_prefix="/admin/filters")

#endregion

if app.config["DEBUG"]:
    CORS(app)
    app.config["CORS_HEADERS"] = "Content-Type"
else:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

config = SimpleNamespace(dotenv_values(".env.development" if app.config["DEBUG"] else ".env"))

valkey_host = config.VALKEY_HOST if config.VALKEY_HOST else "localhost"
postgres_host = config.POSTGRES_HOST if config.POSTGRES_HOST else "localhost"

user_auth = AuthManager(host=valkey_host)
provider = ValkeyInformationProvider(app, valkey_host)
esi = ESI(config.CLIENT_ID, config.CLIENT_SECRET)

if "vite" not in sys.argv:
    corp_id = CorpID(BaseID(int(config.CORP_ID)))
    engine = sa.create_engine(f"postgresql://postgres:wuagmeister@{postgres_host}")
    contracting_thread = threading.Thread(
        target=pull_contracts,
        name="Puller Thread",
        args=(esi, corp_id, valkey_host, engine),
        daemon=True,
    )

    contracting_thread.start()
    valkey_client = Valkey(valkey_host, decode_responses=True)
    register_blueprints(app, valkey_client, esi)


#region Inertia helpers
def get_current_user():
    return json.dumps(current_user.__dict__)

def get_messages():
    return json.dumps(get_flashed_messages(with_categories=True))

def get_is_admin():
    return admin_permissions.can()

# Shared data
inertia.share("client_id", config.CLIENT_ID)
inertia.share("scopes", config.SCOPES)
inertia.share("redirect_uri", config.REDIRECT_URI)
inertia.share("current_user", get_current_user)
inertia.share("messages", get_messages)
inertia.share("is_admin", get_is_admin)

#endregion

#region Routes 

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

    response = esi.get_tokens(login_code)

    token_data: dict[str, str] = decode_token(response.access_token)
    character_id: str = token_data["sub"].split(":")[2]

    corp_id = esi.get_character_corp(int(character_id))
    if corp_id != int(config.CORP_ID):
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
        return get_outstanding_contracts(corp_id, engine)

    props = {"contracts": get_contracts}
    return render_inertia("Contracts", props)

@app.post("/contracts/open")
@login_required
def open_contract():
    options: dict[str, Any] = cast(dict[str, Any], request.json)
    print(f"Getting key for {current_user.id}")
    key = get_key(esi, current_user.id, valkey_client)

    if "id" in options:
        open_corp_contract(options["id"], key)

    return redirect(request.referrer, 303)

@app.route("/fuelling")
@login_required
def fuelling():
    return render_inertia("Fuelling")


@app.route("/admin")
@login_required
@admin_permissions.require(http_exception=403)
def admin():
    props = {}
    filters : set[bytes] = cast(set[bytes], valkey_client.smembers("filters"))

    if filters:
        props.update({
            "filters": [json.loads(x) for x in filters]
        })
    else:
        props.update({
            "filters": []
        })


    return render_inertia("Admin", props=props)

#endregion
