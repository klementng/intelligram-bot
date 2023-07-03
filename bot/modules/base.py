import bot.modules.weather.api.gov_sg as api
import io
import json
import datetime
import requests
import random
import random
from requests.exceptions import HTTPError
from bot.helper.templates import render_response_template

from telegrambots.wrapper import TelegramBotsClient
from telegrambots.wrapper.types.api_method import TelegramBotsMethod
from telegrambots.wrapper.types.methods import *
from telegrambots.wrapper.types.objects import *

from bot.core.objects import UserSession
import bot.core.database as db
import pickle
from dataclasses import dataclass, KW_ONLY
from dataclasses_json import dataclass_json, DataClassJsonMixin


from telegrambots.wrapper.types.api_method import TelegramBotsMethod
from telegrambots.wrapper.types.methods import SendMessage, EditMessageText, SendPhoto, EditMessageMedia, EditMessageCaption
from telegrambots.wrapper.types.objects import InlineKeyboardMarkup, InlineKeyboardButton, InputFile, CallbackQuery, InputMediaPhoto, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove


class BaseModule:
    hook = "/base"
    description = "Base Module Object"

    def __init__(self, *args, **kwargs) -> None:
        assert (args[0] == self.hook)  # Sanity check
        
        self.args = args
        self.argc = len(args)
        self.tg_obj = kwargs["tg_obj"]
        self.session: UserSession = kwargs["session"]
        self.client: TelegramBotsClient = kwargs["client"]

        if isinstance(self.tg_obj, CallbackQuery):
            self.session.message_id = self.tg_obj.message.message_id

    def is_in_group(self):

        if isinstance(self.tg_obj,CallbackQuery):
            if self.tg_obj.message.chat.type in ["group", "supergroup","channel"]:
                return True
        
        elif isinstance(self.tg_obj,Message):
            if self.tg_obj.chat.type in ["group", "supergroup","channel"]:
                return True
            
        else:
            return False


    async def _text_response(self, text: str,reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove = None, print_label=True, args: list[str] = None, chat_id: int | str = None, message_id: int | str = None,**kwargs) -> list[TelegramBotsMethod]:

        if chat_id == None:
            chat_id = self.session.chat_id
        
        if args == None:
            args = self.args

        if message_id == None:
            message_id = self.session.message_id

        if print_label == True and args != None:

            args = list(args)

            for i in range(len(args)):
                if " " in args[i]:
                    args[i] = f"'{args[i]}'"

            text = f"[<pre>{' '.join(args)}</pre>]\n" + text

        if args != None and len(args) > 1 and (isinstance(reply_markup, InlineKeyboardMarkup) or reply_markup == None):

            back_button = InlineKeyboardButton(
                "<< Back <<", callback_data=" ".join(args[:-1]))

            if reply_markup == None:
                reply_markup = InlineKeyboardMarkup([[back_button]])
            else:
                reply_markup.inline_keyboard.append([back_button])

        if message_id == None or isinstance(reply_markup, (ReplyKeyboardMarkup, ReplyKeyboardRemove,)):

            response = SendMessage(
                chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_notification=True,
                **kwargs
            )

        else:

            response = EditMessageText(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup,
                parse_mode="HTML",
                **kwargs
            )

        return [response]

    async def _exception_response(self, text: str,reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove = None, print_label=True, args: list[str] = None, chat_id: int | str = None, message_id: int | str = None,**kwargs) -> list[TelegramBotsMethod]:
        text = f"{text}\n\nts:{datetime.datetime.now()}"

        if args != None and len(args) > 1:

            if reply_markup == None:
                reply_markup = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton(
                            "Retry", callback_data=" ".join(args))],
                    ]
                )

        return await self._text_response(text,args=args, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup,**kwargs)

    async def _photo_response(self,photo: bytes, filename: str, caption: str = None, reply_markup: InlineKeyboardMarkup = None, args: list[str] = None, chat_id: int | str = None, message_id: int | str = None, **kwargs):
        
        if chat_id == None:
            chat_id = self.session.chat_id
        
        if args == None:
            args = self.args

        if message_id == None:
            message_id = self.session.message_id


        file = InputFile(io.BufferedReader(io.BytesIO(photo)), filename)

        # if len(args) > 1:

        #     back_button = InlineKeyboardButton("<< Back <<", callback_data=" ".join(args[:-1]))

        #     if reply_markup == None:
        #         reply_markup = InlineKeyboardMarkup([[back_button]])
        #     else:
        #         reply_markup.inline_keyboard.append([back_button])

        if message_id != None:

            return [
                EditMessageMedia(InputMediaPhoto(
                    file, caption=caption), chat_id, message_id, reply_markup=reply_markup)
            ]

        else:
            return [SendPhoto(chat_id, file, caption=caption, reply_markup=reply_markup)]
