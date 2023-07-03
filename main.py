import os
import requests
import logging

import bot.core.database as db
import bot.core.server as server
from bot.modules import *

logging.basicConfig(format= "[%(asctime)s] [%(levelname)-5s] [%(name)-20s] -- %(message)s (%(filename)s:%(lineno)s) ")
logging.getLogger('werkzeug').disabled = True
logging.getLogger().setLevel(logging.DEBUG)

os.environ["BOT_CONFIG_DIR"] = os.getenv('BOT_CONFIG_DIR',"/config")
if os.getenv("BOT_TOKEN") == None:
    raise EnvironmentError("The Environmental Variable BOT_TOKEN is required")


if __name__ == "__main__":

    db.setup()
    server.setup([
        StartModule, 
        WeatherModule,
        ShortcutsModule, ScShow, 
        CatGPTModule
    ])
    
    server.run(debug=True)
