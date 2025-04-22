# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/20/2025 3:48 PM
# @Function:
import logging
import threading
import time

import pymongo


def get_mongo_client(host) -> tuple[bool, any]:
    try:
        client = pymongo.MongoClient(host)
        client.list_database_names()
        time.sleep(0.1)
        return True, client
    except Exception as e:
        logging.warning(f"Error: {e}")
        return False, None


_is_getting = False


def get_mongo_client_async(host, callback):
    global _is_getting
    if _is_getting:
        logging.warning("Another task is running")
        return

    def _get_mongo_client():
        global _is_getting
        _is_getting = True
        success, client = get_mongo_client(host)
        if success and callback is not None:
            callback(client)
        _is_getting = False

    threading.Thread(target=_get_mongo_client).start()


def is_getting_mongo_client() -> bool:
    return _is_getting
