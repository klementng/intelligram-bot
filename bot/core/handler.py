"""
Module for handling supported telegram request
"""

from telegrambots.wrapper.types.methods import AnswerCallbackQuery, SendMessage
from telegrambots.wrapper.types.objects import *
from telegrambots.wrapper import TelegramBotsClient
from bot.core.objects import UserSession
import bot.core.server as server 

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
    user_id = tg_obj.from_user.id if tg_obj.from_user.id != None else 0
    text = tg_obj.text if tg_obj.text != None else ''

    log.info(f"Processing Message from user:{user_id}, chat:{chat_id}")
    log.debug(f"Content: '{text}', user:{user_id}, chat:{chat_id}")

    session = UserSession(user_id, chat_id)

    if text == '' or re.match("/.*[@[a-zA-Z]*]?",text) == None:
        log.debug(f"Message is not a text / does not contain a command, checking previous session")
        is_addl_args, last_command = await session.async_get_state()

        text = last_command + " " + text if is_addl_args else text
    
    try:
        await async_handle_request(client,tg_obj,session,text)
    except Exception as e:
        async with client:
            await client(SendMessage(chat_id, f"ERROR: Not a command / sessions missing / unsupported object. \n\nTry running a command e.g. /start: {e}", reply_to_message_id=tg_obj.message_id))

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

    try:
        await async_handle_request(client,tg_obj,session,text)
    except Exception as e:
        async with client:
            await client(SendMessage(chat_id,str(e)))

    log.info("Completed CallbackQuery Request")


async def async_handle_request(client,tg_obj,session,text):
    text = re.sub("[@[a-zA-Z]*]",'',text)
    text = text.strip()
    
    module = re.search("/\S*", text)
    module = module.group(0) if module != None else None
    module = server.ENABLED_MODULES[module]
    
    kwargs = {
        "client": client,
        "tg_obj": tg_obj,
        "session": session,
        'text': text
    }
    await module.handle_request(**kwargs)