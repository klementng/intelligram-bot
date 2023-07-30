import json
import sqlite3
import shlex
from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin

from typing import Iterable

from telegrambots.wrapper.types.api_method import TelegramBotsMethod
from telegrambots.wrapper.types.methods import SendMessage, EditMessageText, SendPhoto, EditMessageMedia, EditMessageCaption
from telegrambots.wrapper.types.objects import InlineKeyboardMarkup, InlineKeyboardButton, InputFile, CallbackQuery, InputMediaPhoto


import bot.core.database as db
from bot.core.objects import UserSession
from bot.modules import BaseModule

from bot.helper.templates import render_response_template


class ShortcutsModule(BaseModule):
    """
    Module that handles a commands received from user.

    This modules allow the user to saved favorite. Does not need be instantiated

    Class Attributes:
        hook: trigger modules activation [async default: "/shortcuts"]
        description: modules description

    """

    hook = "/shortcuts"
    description = "Set custom inline keyboard"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.command_list = []

    async def _print_command_list(self, command_list=None):
        if command_list == None:
            command_list = self.command_list

        text = "\nSaved Commands:\n"

        if len(command_list) == 0 :
            text = text + "[no saved commands]\n"

        for i, command in enumerate(command_list):
            for name, data in command.items():
                text = text + f"{i}. {name} '{data}'\n"

        return text

    async def _db_get(self) -> list[dict]:
        """
        Query database for saved command list. 

        Returns:
            list of key:value pair

        Raises:
            sqlite3.Error: Database error
        """
        query = db.execute(
            "SELECT command_list FROM Shortcuts WHERE user_id = ?", (self.session.user_id,))

        self.command_list = json.loads(query[0][0]) if (query != []) else []

        return self.command_list

    async def _db_add(self, name, command) -> list[dict]:
        """
        Adds a new shortcuts. 

        Returns: 
            list of command stored in db

        Raises: 
            sqlite3.Error: Database error
        """

        self.command_list.append({name: command})

        db.execute_and_commit(
            """
            INSERT INTO shortcuts 
            VALUES(:user_id,:command_list) 
            ON CONFLICT(user_id) 
            DO UPDATE SET command_list=:command_list 
            WHERE user_id = :user_id
            """,
            {
                "user_id": self.session.user_id,
                "command_list": json.dumps(self.command_list)
            }
        )

        return self.command_list

    async def _db_delete(self, indexes: Iterable[int]) -> list[dict]:
        """
        Delete a shortcuts. 

        Returns: 
            A message

        Raises: 
            sqlite3.Error: Database error
            IndexError: Invalid Indexes
        """

        old_list = self.command_list

        self.command_list = [i for j, i in enumerate(
            old_list) if j not in indexes]

        if len(self.command_list) == 0:
            sql = "DELETE from shortcuts WHERE user_id = :user_id;"

        else:
            sql = """
                UPDATE shortcuts SET command_list = :command_list
                WHERE user_id = :user_id;
                """

        db.execute_and_commit(
            sql,
            {
                "user_id": self.session.user_id,
                "command_list": json.dumps(self.command_list)
            }
        )
        return self.command_list

    async def _db_edit(self,index: int, name: str, command: str) -> list[dict]:
        """
        Edit a saved shortcut. 

        Returns: 
            A message

        Raises: 
            sqlite3.Error: Database error
            IndexError: Invalid index
        """

        self.command_list[index] = {name: command}

        sql = """ 
            UPDATE shortcuts SET command_list = :command_list
            WHERE user_id = :user_id;
            """

        db.execute_and_commit(sql, {
            "user_id": self.session.user_id,
            "command_list": json.dumps(self.command_list)
        })

        return self.command_list

    async def _shortcuts_show_response(self) -> list[TelegramBotsMethod]:
        """Query database and replies with a message with InlineMarkup"""

        assert self.args[1] == "show"

        self.command_list = await self._db_get()

        if self.command_list != []:

            button_list = []
            for i, command in enumerate(self.command_list):
                for name, data in command.items():

                    button_list.append([InlineKeyboardButton(
                        f"{i}. " + name, callback_data=str(data))])

            reply_markup = InlineKeyboardMarkup(button_list)

            return await self._text_response("Saved shortcut list", reply_markup)
        else:
            return await self._text_response("Your shortcut list is empty")

    async def _shortcuts_add_response(self) -> list[TelegramBotsMethod]:
        if self.argc != 5:
            return await self._text_response(f'Too many/few arguments: \n\nExpected 5 for "add""', args=self.args[0:2])

        new_list = await self._db_add(self.args[3], self.args[4])
        text = "Added!\n" + await self._print_command_list(new_list)
        return await self._text_response(text,args=self.args[0:2])

    async def _shortcuts_delete_response(self) -> list[TelegramBotsMethod]:

        if self.argc < 4:
            return await self._text_response(f'Too few arguments: \n\nExpected >= 4 for "add""', args=self.args[0:2])

        try:
            indexes = tuple(map(int, self.args[3:]))
            new_list = await self._db_delete(indexes)
            text = "Deleted!\n" + await self._print_command_list(new_list)

            return await self._text_response(text,args=self.args[0:2])

        except (ValueError, IndexError) as e:
            await self.session.async_update_state(self.args[0:2], True)
            return await self._text_response(f"Invalid index(es): \n\n {e}", args=self.args[0:2])

    async def _shortcuts_edit_response(self) -> list[TelegramBotsMethod]:
        if self.argc != 6:
            return await self._text_response(f'Too many/few arguments: \n\nExpected 6 for "edit""', args=self.args[0:2])

        try:
            index = int(self.args[3])
            new_list = await self._db_edit(index, self.args[4], self.args[5])
            text = "Edited!\n" + await self._print_command_list(new_list)

            return await self._text_response(text,args=self.args[0:2])

        except (ValueError, IndexError) as e:
            await self.session.async_update_state(self.args[0:2], True)
            return await self._text_response(f"Invalid Index: \n\n {e}", args=self.args[0:2])

    async def _shortcuts_modify_response(self) -> list[TelegramBotsMethod]:
        """Modify the shortcuts list"""

        assert (self.args[1] == "modify")

        if self.argc == 2:
            self.command_list = await self._db_get()

            text = render_response_template(
                "shortcuts/templates/modify.html"
            )

            text = text + await self._print_command_list(self.command_list)

            await self.session.async_update_state(self.args, require_addl_args=True)
            return await self._text_response(text)

        # Check if enough arguments
        elif self.argc < 4:
            await self.session.async_update_state(self.args[0:2], True)
            return await self._text_response(f"Not enough arguments, expected > 3, got {self.argc}", args=self.args[0:2])

        action = self.args[2].lower()
        await self.session.async_update_state(self.args[0:2], True)
        if action == "add":
            return await self._shortcuts_add_response()

        elif action == "delete":
            return await self._shortcuts_delete_response()

        elif action == "edit":
            return await self._shortcuts_edit_response()

        else:
            await self.session.async_update_state(self.args[0:2], True)

            return await self._text_response(
                f'Unexpected Arguments: "{action}"',
                args=self.args[0:2],
            )

    async def _shortcuts_help_response(self) -> list[TelegramBotsMethod]:
        """Render and send the help response"""

        assert (self.args[1] == "help")
        msg = render_response_template(
            "shortcuts/templates/help.html", hook=self.hook)

        return await self._text_response(msg)

    async def _shortcuts_hook_response(self):
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "Show", callback_data=f"{self.hook} show"),
            InlineKeyboardButton(
                "Modify", callback_data=f"{self.hook} modify"),
            InlineKeyboardButton(
                "Help", callback_data=f"{self.hook} help")
        ]])

        return await self._text_response(f"Select an option", reply_markup)


    @classmethod
    async def handle_request(cls, **kwargs) -> list[TelegramBotsMethod]:
        """
        Get replies for commands:

        Args (required):
            *args: parsed user inputs
            **user_id: chat_id
            **session: UserSession = None Object

        Return:
            list of TelegramBotsMethod

        Raises:
            ValueError: chat_id does not exist / not an int
        """

        args = shlex.split(kwargs['text'])

        slf = cls(*args,**kwargs)
        await slf.session.async_update_state(args,False)

        assert (args[0] == slf.hook)

        if len(slf.args) == 1:
            res = await slf._shortcuts_hook_response()

        else:
            slf.command_list = await slf._db_get()
            try:
                res =  await getattr(slf, '_shortcuts_%s_response' % args[1])()

            except AttributeError:
                res = await slf._exception_response(f"Unexpected argument: '{args[1]}'",args=slf.args[0:1])
        
        async with slf.client as client:
            for r in res:
                await client(r)


class ScShow(ShortcutsModule):
    hook = "/scshow"
    description = "Show Saved Shortcuts"

    async def handle_request(self, **kwargs) -> list[TelegramBotsMethod]:
        kwargs['text'] = f'{ShortcutsModule.hook} show'
        return await ShortcutsModule.handle_request(**kwargs)