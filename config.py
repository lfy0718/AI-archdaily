# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/12/2025 10:06 AM
# @Function:
import atexit
import json
import logging
import os

PROJECT_NAME = "AI-Archdaily"
RESOURCES_DIR = "./resources"


class UserSettings:
    def __init__(self):
        # these are default values
        self.base_url = "https://www.archdaily.com/"
        self.projects_dir = './results/projects'
        self.invalid_project_ids_path = './results/invalid_project_ids.json'

        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Cache-Control": "max-age=0",
            "Host": "www.archdaily.com",
            "Priority": "u=0, i",
            "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
        }
        self.ignore_keywords = {
            "Projects", "Images", "Products", "Folders", "AD Plus",
            "Benefits", "Archive", "Content", "Maps", "Audio",
            "Check the latest Chairs", "Check the latest Counters"
        }
        self.mongodb_host = 'mongodb://localhost:32769/?directConnection=true'
        self.mongodb_db_name = 'AI-Archdaily'


def load_user_settings(_user_settings: UserSettings) -> None:
    data_path = "./user_settings.json"
    logging.info(f'loading user_settings from {os.path.abspath(data_path)}')
    if os.path.exists(data_path):
        with open(data_path, "r") as file:
            json_data: dict = json.load(file)
        for key in _user_settings.__dict__.keys():
            if key in json_data:
                if key == "ignore_keywords":
                    setattr(_user_settings, key, set(json_data[key]))
                else:
                    setattr(_user_settings, key, json_data[key])
            else:
                logging.debug(f"    [warning] {key} not found in json, use default value")
    else:
        logging.info(f'user_settings file not found, use default user_settings')


def save_user_settings(_user_settings: UserSettings) -> None:
    assert _user_settings is not None, "user_settings is None"
    data_path = "./user_settings.json"
    logging.info(f'saving user_settings to {os.path.abspath(data_path)}')
    data = {}
    for key in _user_settings.__dict__:
        if key == "ignore_keywords":
            data[key] = list(getattr(_user_settings, key))
        else:
            data[key] = getattr(_user_settings, key)
    json_data = json.dumps(data, indent=4)
    with open(data_path, "w") as file:
        file.write(json_data)
    logging.info(f'Successfully write user_settings to {os.path.abspath(data_path)}')


user_settings: UserSettings = UserSettings()
load_user_settings(user_settings)  # load user settings on start

atexit.register(save_user_settings, user_settings)