import bot.modules.weather.api.gov_sg as api
import io
import yaml
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

from ..base import BaseModule
from bot.core.objects import UserSession
import bot.core.database as db



import pickle
from dataclasses import dataclass, KW_ONLY
from dataclasses_json import dataclass_json, DataClassJsonMixin


@dataclass
class CatGPTSettings(DataClassJsonMixin):

    _: KW_ONLY
    send_gif: bool = True

    # Required for AI
    email: str = None
    Authorization: str = None

    # Remembers last session
    threadId: str | int = None
    isNewThread: bool = None

    async def async_update_db(self, user_id):
        db.execute_and_commit(
            """
            INSERT INTO CatGPT
            VALUES(:user_id,:settings_json)
            ON CONFLICT(user_id)
            DO UPDATE SET settings_json=:settings_json
            WHERE user_id = :user_id
            """,
            {
                "user_id": user_id,
                "settings_json": self.to_json()
            }
        )

    @classmethod
    async def async_load_from_db(cls, user_id):
        return cls.load_from_db(user_id)
    
    @classmethod
    def load_from_db(cls, user_id):
        query = db.execute(
            "SELECT settings_json FROM CatGPT WHERE user_id = ?", (user_id,))

        if len(query) == 1:
            return cls.from_json(query[0][0])
        else:
            return cls()
    

class CatGPTModule(BaseModule):
    hook = "/catgpt"
    description = "Talk to a Cat!"

    def __init__(self,*args, **kwargs) -> None:
        super().__init__(*args,**kwargs)
        self.settings = CatGPTSettings.load_from_db(self.session.user_id)


    async def _catgpt_split_send_response(self, text: str, gif=None):
        "Send responses in a AI like way with delay"

        text_list = text.split(" ")
        chat_id = self.session.chat_id

        async with self.client:
            if self.settings.send_gif == True and gif != None:
                msg_obj: Message = await self.client(SendDocument(chat_id, gif))    
                return [EditMessageCaption(msg_obj.chat.id, msg_obj.message_id, caption=" ".join(text_list[0:i+1])) for i in range(len(text_list))]
            
            else:
                msg_obj: Message = await self.client(SendMessage(chat_id, text_list[0]))
                return [EditMessageText(" ".join(text_list[0:i+2]), msg_obj.chat.id, msg_obj.message_id) for i in range(len(text_list)-1)]

    async def _catgpt_meow_fetch_api(self):
        return f"https://www.cat-gpt.com/cats/gif?{datetime.datetime.now().microsecond}", "CAT:" + " meow" * random.randint(1, 10)

    async def _catgpt_meow_response(self):
        if self.argc <= 3:
            await self.session.async_update_state(self.args[0:3], True)
            return await self._text_response("CAT: Meow?")

        else:
            gif, text = await self._catgpt_meow_fetch_api()
            await self.session.async_update_state(self.args[0:3], True)

            return await self._catgpt_split_send_response(text, gif)

    async def _catgpt_ai_fetch_api(self, prompt: str):
        headers = {
            "Authorization": self.settings.Authorization,
            "Content-Type": "application/json",
        }

        if self.settings.isNewThread == True:
            payload = json.dumps(
                {"userPrompt": "", "email": self.settings.email, "threadId": self.settings.threadId, "userRequests": [
                    {"role": "system", "content": "Respond to whatever I say here as if you’re a sassy cat that cares about me but doesn’t want me to know, and you want to be helpful but you want me to want you to be helpful. Make sure to sprinkle in some meows every now and then, especially when replacing words like now and how."},
                    {"role": "user", "content": str(self.settings.threadId) + " " + prompt}], "isNewThread": True
                 }
            )

            self.settings.isNewThread = False
            await self.settings.async_update_db(self.session.user_id)

        else:
            payload = json.dumps(
                {"userPrompt": "", "email": self.settings.email, "threadId": self.settings.threadId, "userRequests": [{"role": "user", "content": prompt}], "isNewThread": False})

        
        try:
            re = requests.put("https://cat-gpt.com/api/conversation",data=payload, headers=headers)
            re.raise_for_status()
            text = "CAT:" + re.json()["data"]["message"]["content"]
        
        except Exception as e:
            raise HTTPError(e)

        return f"https://www.cat-gpt.com/cats/gif?{datetime.datetime.now().microsecond}", text

    async def _catgpt_ai_session(self):
        if self.settings.email == None or self.settings.Authorization == None:

            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(
                "Update Settings", callback_data=f"{self.hook} settings")]])

            return await self._text_response(f"Missing email/api auth header, update setting to use ai mode", reply_markup)

        elif self.argc == 3:
            reply_markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "New", callback_data=f"{self.hook} chat ai new"),
                        InlineKeyboardButton(
                            "Resume", callback_data=f"{self.hook} chat ai resume")
                    ]
                ]
            )

            return await self._text_response(f"New or Resume Session", reply_markup)

        elif self.argc == 4:

            if self.args[3] == "resume" and self.settings.threadId != None:
                thread_id = self.settings.threadId
            else:
                thread_id = str(random.randint(1, 9000000000000000))

                self.settings.threadId = thread_id
                self.settings.isNewThread = True
                await self.settings.async_update_db(self.session.user_id)

            self.args = self.args[0:3] + (thread_id,)

            await self.session.async_update_state(self.args, True)
            return await self._text_response("CAT: Meow?")

    async def _catgpt_ai_response(self):
        assert self.args[2] == "ai"

        if self.argc < 5:
            return await self._catgpt_ai_session()
        
        prompt = " ".join(self.args[4:])

        self.args = self.args[0:4]

        try:
            gif, text = await self._catgpt_ai_fetch_api(prompt)
            
        except Exception as e:
            await self.session.async_update_state(self.args, True)
            return await self._exception_response("API Error\n\n" + str(e))

        await self.session.async_update_state(self.args, True)

        return await self._catgpt_split_send_response(text, gif)

    async def _catgpt_chat_response(self):
        assert self.args[1] == "chat"

        if self.argc < 3:
            reply_markup = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(
                        "Mode 1: Meows", callback_data=f"{self.hook} chat meow ")],
                    [InlineKeyboardButton(
                        "Mode 2: AI", callback_data=f"{self.hook} chat ai")]
                ]
            )

            return await self._text_response(f"Select an option", reply_markup)

        elif self.args[2] == "meow":
            return await self._catgpt_meow_response()

        elif self.args[2] == "ai":
            return await self._catgpt_ai_response()

    async def _catgpt_settings_response(self):
        assert self.args[1] == "settings"
        
        settings = self.settings.to_dict()

        if self.is_in_group() == True:
            return await self._text_response("Editing of settings is not allowed in group chat",args=self.args[0:2])

        if self.argc == 2:
            self.session.update_state(self.args,True)

            return await self._text_response(render_response_template("catgpt/templates/settings.html",yaml_str=yaml.dump(settings)))
        
        elif self.argc > 3:
            try:
                user_dict = yaml.safe_load(self.tg_obj.text)
                user_setting = CatGPTSettings.from_dict(user_dict)
                await user_setting.async_update_db(self.session.user_id)
                return await self._text_response("Success!",args=self.args[0:2])

            except:
                await self.session.update_state(self.args,True)
                return await self._exception_response("Invalid YAML format")

        else:
            return await self._exception_response("Too many arguments expected 3")

    async def _catgpt_help_response(self):
        assert (self.args[1] == "help")
        msg = render_response_template(
            "catgpt/templates/help.html", hook=self.hook)

        return await self._text_response(msg)

    async def _catgpt_hook_response(self):
        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(
                    "Mode 1: Meows", callback_data=f"{self.hook} chat meow ")],
                [InlineKeyboardButton(
                    "Mode 2: AI", callback_data=f"{self.hook} chat ai")],
                [InlineKeyboardButton(
                    "Settings", callback_data=f"{self.hook} settings")],
                [InlineKeyboardButton(
                    "Help", callback_data=f"{self.hook} help")],
            ]
        )

        return await self._text_response(f"Select an option", reply_markup)

    @classmethod
    async def handle_request(cls, **kwargs) -> list[TelegramBotsMethod]:
        args = kwargs['text'].split(" ")

        slf = cls(*args, **kwargs)
        await slf.session.async_update_state(args,False)

        if slf.argc == 1:
            res =  await slf._catgpt_hook_response()

        elif slf.args[1] == "settings":
            res =  await slf._catgpt_settings_response()

        elif slf.args[1] == "chat":
            res =  await slf._catgpt_chat_response()
        
        elif slf.args[1] == "help":
            res=  await slf._help_response()
        
        else:
            res = await slf._exception_response(f"Invalid Argument: '{slf.args[1]}'")

        async with slf.client as client:
            for r in res:
                await client(r)