"""
Module for handling supported telegram request
"""

from telegrambots.wrapper.types.methods import AnswerCallbackQuery, SendMessage
from telegrambots.wrapper.types.objects import *
from telegrambots.wrapper import TelegramBotsClient
from bot.core.objects import UserSession
import bot.core.server as server 

import shlex
import logging
import re

log = logging.getLogger(__name__)

async def async_process_update(token, tg_update: Update):
    """Process incoming telegram update object"""

    client = TelegramBotsClient(token)
    tg_obj = tg_update.actual_update

    log.info(f"Received telegram update object ...")

    if isinstance(tg_obj, Message):
        await async_handle_message(client, tg_obj)

    elif isinstance(tg_obj, CallbackQuery):
        await async_handle_callback_query(client, tg_obj)

    else:
        log.error("Unsupported telegram object, update not processed")


async def async_handle_message(client: TelegramBotsClient, tg_obj: Message):
    """Parse message objects"""

    chat_id = tg_obj.chat.id
    user_id = tg_obj.from_user.id if not None else 0
    text = tg_obj.text

    log.info(f"Processing Message from user:{user_id}, chat:{chat_id}")
    log.debug(f"Content: '{text}', user:{user_id}, chat:{chat_id}")

    session = UserSession(user_id, chat_id)

    # if tg_obj.entities != None:
    #     for e in tg_obj.entities:
    #         if e.type == "bot_command":
    #             is_command = True
    #             text = re.sub("@[a-zA-Z]*"," ",text).strip()
    #             log.debug(f"Message contain a bot_command entity, skipping session check")
    #         elif e.type == "mention":
    #             text = re.sub("@[a-zA-Z]*"," ",text).strip()

    is_command = False
    if isinstance(text, str):
        text = re.sub("@[a-zA-Z]*", " ", text).strip()  # remove mentions

        if text.startswith("/"):
            is_command = True

            if "/start" not in text: # prevent database entry
                await session.async_update_state(text, False)  # reset status state

    # Not a text object or Not a command
    if text == None or is_command == False:
        log.debug(f"Message does not contain a entity, checking previous session")
        is_addl_args, last_command = await session.async_get_state()

        if is_addl_args == True:

            text = "" if text == None else text
            text = last_command + " " + text

            log.debug(f"Previous session found, appending args")
            log.debug(f"Content: '{text}', user:{user_id}, chat:{chat_id}")

        elif tg_obj.chat.type in ["group", "supergroup", "channel"]:
            log.debug(f"Previous session not found, chat type is group, ignoring message")
            return

        else:
            async with client:
                await client(SendMessage(chat_id, "ERROR: Not a command / sessions missing / unsupported object. \n\nTry running a command e.g. /start", reply_to_message_id=tg_obj.message_id))

            log.debug(f"USER ERROR: Previous session not found, no command is found")
            return

    success, error_msg = await async_send_response(client, session, tg_obj, text)
    if success == False:
        async with client:
            await client(SendMessage(chat_id, error_msg, reply_to_message_id=tg_obj.message_id))

    log.info("Completed Message request")


async def async_handle_callback_query(client: TelegramBotsClient, tg_obj: CallbackQuery):
    """Parse CallbackQuery objects"""

    async with client:
        await client(AnswerCallbackQuery(tg_obj.id))

    chat_id = tg_obj.message.chat.id
    user_id = tg_obj.from_user.id if not None else 0
    text = tg_obj.data

    log.info(f"Processing CallbackQuery from user:{user_id}, chat:{chat_id}")
    log.debug(f"Content: '{text}', user:{user_id}, chat:{chat_id}")

    session = UserSession(user_id, chat_id)
    await session.async_update_state(text, False)

    success, error_msg = await async_send_response(client, session, tg_obj, text)
    if success == False:
        async with client:
            await client(SendMessage(chat_id, error_msg))

    log.info("Completed CallbackQuery Request")


async def async_send_response(client, session, tg_obj, text):
    """Send parsed telegram object to respective modules"""

    log.debug("Processing requests in modules")

    try:
        lexer = shlex.shlex(text)
        lexer.quotes = "'\""
        lexer.whitespace_split = True
        lexer.commenters = ""

        args = [s.replace('\"', "") for s in lexer]
        args[0] = args[0].lower()

        module = server.ENABLED_MODULES[args[0]]

    except ValueError as e:
        log.debug("USER ERROR: Parsing")
        return False, f"Parsing Error {e}"

    except KeyError as e:
        log.debug("USER ERROR: Unknown / Missing command / Unsupported Object")
        return False, f"Unknown command / Unsupported object: '{args[0]}'"

    except TypeError as e:
        log.debug("USER ERROR: Unknown Object")
        return False, f"Unknown Object: '{args[0]}'"


    try:
        kwargs = {
            "tg_obj": tg_obj,
            "session": session,
            "client": client
        }
        responses = await module.get_response(*args, **kwargs)

        async with client:
            for method in responses:
                await client(method)

        return True, ""
    
    except Exception as e:
        if "message is not modified" in str(e):
            return True, ""

        log.error("An error occurred while processing request in module",exc_info=True)
        return False, f"Unexpected Error:\n\n{e}"
    