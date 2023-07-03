"""
Module for interfacing with sqlite database

ENVIRONMENTAL VARIABLES
-----------------------
BOT_DB_PATH:
    Path to SQlite database file. Defaults "{BOT_CONFIG_DIR}/data/data.db"
"""

import os
import sqlite3
import logging

_SETUP_COMPLETED = False

log = logging.getLogger(__name__)

DB_PATH = os.getenv('BOT_DB_PATH',
                    os.path.join(os.getenv("BOT_CONFIG_DIR"),"data/data.db")
                    )


def setup(path=None) -> None:
    """Configures database file and schema"""

    log.debug("Configuring database...")

    if path != None:
        global DB_PATH
        DB_PATH = path
        log.debug(
            "path argument is set, environmental variable DB_PATH is overwritten")

    try:

        # Create directory and file
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        if not os.path.isfile(DB_PATH):
            with open(DB_PATH, "w") as db_file:
                db_file.close()

        # create database schema
        execute_and_commit(
            """
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT
            ) WITHOUT ROWID;
        """
        )

        execute_and_commit(
            """
            CREATE TABLE IF NOT EXISTS UserSession (
                chat_id INTEGER,
                user_id INTEGER,
                command TEXT,
                listening BOOL,
                PRIMARY KEY (chat_id, user_id),
                FOREIGN KEY(user_id) REFERENCES Users(id)
            );
        """
        )

        execute_and_commit(
            """
            CREATE TABLE IF NOT EXISTS Shortcuts (
                user_id INTEGER PRIMARY KEY,
                command_list TEXT,
                FOREIGN KEY(user_id) REFERENCES Users(id)
            );
        """
        )

        execute_and_commit(
            """
            CREATE TABLE IF NOT EXISTS CatGPT (
                user_id INTEGER PRIMARY KEY,
                settings_json TEXT
            ) WITHOUT ROWID;
        """
        )

        global _SETUP_COMPLETED
        _SETUP_COMPLETED = True

    except:
        log.fatal("Unable to setup database", exc_info=True)
        exit(1)


def commit():
    """
    Commit changes to database
    """

    with sqlite3.connect(DB_PATH) as con:
        con.commit()


def execute(sql: str, format: tuple | dict = ()) -> list[tuple]:
    """
    Execute sql queries without committing

    Parameters
    ----------
    sql: str
        sql queries

    format: tuple | dict, optional
        parameters to bind values in sql

    Returns
    -------
        list[tuple]
            results of sql statement
    """

    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()

        return cur.execute(sql, format).fetchall()


def execute_and_commit(sql: str, format: tuple | dict = ()) -> list[tuple]:
    """
    Execute sql queries and committing changes 

    Parameters
    ----------
    sql: str
        sql queries

    format: tuple | dict, optional
        parameters to bind values in sql

    Returns
    -------
        list[tuple]
            result of sql statement
    """

    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()

        res = cur.execute(sql, format).fetchall()
        con.commit()

        return res


async def async_commit(sql: str, format: tuple | dict = ()) -> list[tuple]:
    """
    Asynchronously commit changes to database
    """

    return execute(sql, format)


async def async_execute(sql: str, format: tuple | dict = ()) -> list[tuple]:
    """
    Asynchronously Execute sql queries without committing

    Parameters
    ----------
    sql: str
        sql queries

    format: tuple | dict, optional
        parameters to bind values in sql

    Returns
    -------
        list[tuple]
            result of sql statement
    """

    return execute(sql, format)


async def async_execute_and_commit(sql: str, format: tuple | dict = ()) -> list[tuple]:
    """
    Asynchronously execute sql queries and committing changes 

    Parameters
    ----------
    sql : str
        sql queries

    format: tuple | dict, optional
        parameters to bind values in sql

    Returns
    -------
        list[tuple]
            result of sql statement
    """
    return execute_and_commit(sql, format)
