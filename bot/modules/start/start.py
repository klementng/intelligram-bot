from telegrambots.wrapper.types.api_method import TelegramBotsMethod
from telegrambots.wrapper.types.methods import *
from telegrambots.wrapper.types.objects import *

import bot.core.server

from ..base import BaseModule
from bot.helper.templates import render_response_template


class StartModule(BaseModule):
    hook = "/start"
    description = "Show All Modules"
    
    @classmethod
    async def handle_request(cls, **kwargs) -> list[TelegramBotsMethod]:
        """
        Get replies for commands:

        Args (required):
            *args: parsed user inputs
            **tg_obj: chat id
            **session: chat id

        Return:
            list of TelegramBotsMethod

        Raises:
            KeyError: Missing kwargs
        """

        args = kwargs['text'].split(" ")

        text = render_response_template(
            "start/templates/start.html", MODULES=bot.core.server.ENABLED_MODULES)
        
        reply_markup = InlineKeyboardMarkup([[
                        InlineKeyboardButton(x.replace("/","").title(), callback_data=x),
        ] for x in bot.core.server.ENABLED_MODULES.keys()][1:])


        res = await cls(*args,**kwargs)._text_response(text,reply_markup)
        async with kwargs['client'] as client:
            for r in res:
                await client(r)


