from typing import Union, Optional, Iterable

import bot.core.database as db

class UserSession:
    """
    Object to allow persistent user session that is stored in database.
    ...

    Attributes
    ----------
    user_id : int | str
        Unique telegram user identification number.
    
    chat_id : int | str
        Unique telegram chat identification number.
    
    message_id : int | str , Optional
        message (if available) corresponding to the in the chat.
    
    """

    def __init__(self, user_id: Union[int, str], chat_id: Union[int, str],message_id: Union[int, str]=None) -> None:
        self.user_id = user_id
        self.chat_id = chat_id
        self.message_id = message_id


    def _run_query(self):
        query = db.execute(
            "SELECT listening,command FROM UserSession WHERE user_id = :user_id AND chat_id = :chat_id", {
                "user_id": self.user_id, "chat_id": self.chat_id}
        )

        if query != []:
            return query[0]
        
        else:
            return False, ''

    def get_state(self):
        """Update user session status and last executed command"""

        return self._run_query()
    
    def update_state(self, command: str | Iterable, require_addl_args: bool):
        """Update user session status and last executed command"""

        if isinstance(command, Iterable):
            command = " ".join(command)

        db.execute_and_commit(
            """
            INSERT INTO UserSession 
            VALUES(:user_id,:chat_id,:command,:listening) 
            ON CONFLICT(chat_id,user_id) 
            DO UPDATE SET 
            command=:command,
            listening=:listening 
            WHERE 
            user_id = :user_id and chat_id = :chat_id
            """,
            {
                "user_id": self.user_id,
                "chat_id": self.chat_id,
                "command": command,
                "listening": require_addl_args
            }
        )

    async def async_get_state(self):
        """Asynchronous get user session status and last executed command"""

        return self._run_query()

    async def async_update_state(self, command: str | Iterable, require_addl_args: bool):
        """Asynchronous update user session status and last executed command"""

        return self.update_state(command,require_addl_args)