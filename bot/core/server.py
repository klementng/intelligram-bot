"""
Core flask server to handle incoming http request

ENVIRONMENTAL VARIABLES
-----------------------

BOT_CONFIG_DIR:
    Path to SQlite database file. Defaults "/config"

BOT_TOKEN:
    Telegram bot api token, required

BOT_SERVER_HOSTNAME: optional
    Hostname or IP address to be published to telegram bot api, defaults "current.public.ip.address"

BOT_SERVER_PUBLISHED_PORT:
    Port to be published to telegram bot api, default 88

BOT_SERVER_PORT:
    Internal flask server port defaults 88

BOT_SERVER_CERT_PATH:
    SSL Cert path, default "{BOT_CONFIG_DIR}/ssl/cert.pem"

BOT_SERVER_KEY_PATH:
    SSL private key path, default "{BOT_CONFIG_DIR}/ssl/key.pem"
    
"""


import json
import os
import requests
import threading
import asyncio

import bot.core.database as db

from bot.core.handler import *
from telegrambots.wrapper.serializations import serialize, deserialize
import requests

from flask import Flask, request, abort

ENABLED_MODULES = {}

# configured in main.py
CONFIG_DIR = os.getenv('BOT_CONFIG_DIR')
BOT_TOKEN = os.getenv('BOT_TOKEN')

HOSTNAME = os.getenv('BOT_SERVER_HOSTNAME') if os.getenv(
    'BOT_SERVER_HOSTNAME') != None else requests.get(
        'https://api.ipify.org').content.decode('utf8')

PUBLISHED_PORT = int(os.getenv('BOT_SERVER_PUBLISHED_PORT', 88))
SERVER_PORT = int(os.getenv('BOT_SERVER_PORT', 88))

# Default values are set later
CERT_PATH = os.getenv('BOT_SERVER_CERT_PATH')
KEY_PATH = os.getenv('BOT_SERVER_KEY_PATH')

_SETUP_COMPLETED = False

flask = Flask(__name__)


def request_callback(args):
    """Run incoming requests in async loops"""

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(async_process_update(BOT_TOKEN, args))
    loop.close()


@flask.route('/', methods=['POST'])
def request_handler():
    """Flask HTTP request handler"""

    if request.method == 'POST':
        api_json = request.json
        tg_update = deserialize(Update, api_json)

        thread = threading.Thread(target=request_callback, args=(tg_update,))
        thread.start()

        return '', 200

    else:
        return '', 400


def run(debug=False):
    """Starts the flask http server"""

    if _SETUP_COMPLETED and db._SETUP_COMPLETED:
        flask.run("0.0.0.0", port=SERVER_PORT, debug=debug, ssl_context=(
            CERT_PATH, KEY_PATH))
    else:
        log.fatal("Failed to setup bot, run server.setup() and db.setup() first", exc_info=True)
        exit(1)


def setup(modules):
    """
    Configures the server

    Parameters
    ----------
        modules: list[BaseModule]
            list of BaseModule object

    """
    global CERT_PATH
    global KEY_PATH
    global ENABLED_MODULES

    ENABLED_MODULES = {m.hook: m for m in modules}

    try:
        # Setup self-signed ssl certs for webhook operations
        if not os.path.isfile(CERT_PATH) or not os.path.isfile(KEY_PATH):
            log.info(
                "ssl cert or key path not set. Using default values ssl/cert.pem & ssl/key.pem")

            CERT_PATH = os.path.join(CONFIG_DIR, "ssl/cert.pem")
            KEY_PATH = os.path.join(CONFIG_DIR, "ssl/key.pem")

            # Generate
            os.makedirs(os.path.join(CONFIG_DIR, "ssl/"), exist_ok=True)
            os.system(
                f'openssl req -x509 -newkey rsa:4096 -keyout {KEY_PATH} -out {CERT_PATH} -sha256 -days 3650 -nodes -subj "/C=US/ST=StateName/L=CityName/O=CompanyName/OU=CompanySectionName/CN={HOSTNAME}"')

        with open(CERT_PATH) as cert:
            url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={HOSTNAME}:{PUBLISHED_PORT}'
            requests.post(url, files={'certificate': cert}).raise_for_status()

        # Setup commands in telegram
        commands_list = [{"command": m.hook.replace(
            "/", ""), "description": m.description} for m in modules]
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands'
        requests.post(url, params={"commands": json.dumps(
            commands_list)}).raise_for_status()

    except Exception as e:
        log.fatal("Failed to setup bot", exc_info=True)
        exit(1)

    global _SETUP_COMPLETED
    _SETUP_COMPLETED = True
