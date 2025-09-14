import datetime
import json
import logging
import sys

from pydantic import ValidationError

from .config import ProgramConfig

sys.path += "."
import platform
import threading
from string import Template
from typing import Any, cast

import sqlalchemy as sa
from flask import Flask, flash, get_flashed_messages, redirect, request
from flask_cors import CORS
from flask_inertia import Inertia, render_inertia
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_principal import Identity, Principal, identity_changed
from flask_vite import Vite
from valkey import Valkey
from werkzeug.middleware.proxy_fix import ProxyFix

from .auth import AuthManager, User, admin_permissions
from .contract_endpoints import BaseID, CorpID, create_contract_blueprint, get_outstanding_contracts, pull_contracts
from .data.data_source import OauthProvider
from .data.esi import ESI
from .data.esi.auth import ESIAuth
from .data.gice.GICE import GICE
from .filters import create_filter_endpoints
from .ValkeyInformationProvider import ValkeyInformationProvider

SECRET_KEY = "AFHFCHDSJCAS"
INERTIA_TEMPLATE = "index.html"

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

# region Flask setup

app = Flask(__name__, static_folder="static")
if platform.system() == "Windows":
    app.config.update({"VITE_NPM_BIN_PATH": "npm.cmd"})

app.config.from_object(__name__)

login_manager = LoginManager(app)
principal = Principal(app)
inertia = Inertia(app)


def register_blueprints(app: Flask, valkey_client: Valkey, esi: ESI):
    contract_endpoints = create_contract_blueprint(corp_id, config.VALKEY_HOST, esi, engine)
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
    Vite(app)
    app.config["CORS_HEADERS"] = "Content-Type"
else:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

try:
    logger.error(f"We are in {"debug" if app.config['DEBUG'] else "production"} mode")
    config = ProgramConfig(_env_file="develop.env" if app.config["DEBUG"] else ".env") # type: ignore
except ValidationError as e:
    logger.error(f"Configuration error: {e}")
    sys.exit(1)

user_auth = AuthManager(host=config.VALKEY_HOST)
provider = ValkeyInformationProvider(app, config.VALKEY_HOST)

if config.AUTH_TYPE == "gice":
    _gice = GICE(config.CLIENT_ID, config.CLIENT_SECRET, config.REDIRECT_URI)
    login_provider: OauthProvider = _gice
    esi = _gice.esi
else:
    esi = ESI()
    login_provider: OauthProvider = ESIAuth(esi,
        config.CLIENT_ID, config.CLIENT_SECRET, config.REDIRECT_URI, scopes=config.SCOPES)

if "vite" not in sys.argv:
    corp_id = CorpID(BaseID(int(config.GROUP_ID)))
    POSTGRES_URL = Template("postgresql://$user:$password@$host")

    engine = sa.create_engine(POSTGRES_URL.substitute(
        user=config.POSTGRES_USER,
        password=config.POSTGRES_PASSWORD,
        host=config.POSTGRES_HOST
    ))

    contracting_thread = threading.Thread(
        target=pull_contracts,
        name="Puller Thread",
        args=(esi, corp_id, config.VALKEY_HOST, engine),
        daemon=True,
    )

  #  contracting_thread.start()
    valkey_client = Valkey(config.VALKEY_HOST, decode_responses=True)
    register_blueprints(app, valkey_client, esi)


#region Inertia helpers
def get_current_user():
    return json.dumps(current_user.__dict__)

def get_messages():
    return json.dumps(get_flashed_messages(with_categories=True))

def get_is_admin():
    return admin_permissions.can()



# Shared data
inertia.share("auth_url", login_provider.get_authorization_url)
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

    token = login_provider.login_user(request.args.get("code", ""))
    logger.info(f"Token received: {token}")

    user_data = login_provider.get_user_info(token.access_token)

    if not login_provider.is_user_in_group(token, int(config.GROUP_ID)):
        flash(f"{user_data.name} is not in the necessary group", "warning")
        app.logger.warning(f"Character {user_data.name} attempted to log in")
        return redirect("/")


    expiration_duration = token.expires_at - datetime.datetime.now(datetime.UTC)

    user_auth.save_user(
        user_id=user_data.id,
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        expiry=int(expiration_duration.total_seconds()),
        name=user_data.name,
    )

    logger.info(f"User {user_data.name} logged in with ID {user_data.id}")
    login_user(User(user_data.id, user_data.name))
    identity_changed.send(app, identity=Identity(user_data.id))
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

    if "id" in options:
        esi.open_corp_contract(options["id"])

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
