
import os
import time

import imgui

from config import *
from dev.components import c
from dev.global_app_state import g
from dev.modules import StyleModule
from dev.windows.base_window import PopupWindow


class SettingsWindow(PopupWindow):
    @classmethod
    def w_init(cls):
        super().w_init()
        # cls.w_open()

    @classmethod
    def w_update(cls):
        super().w_update()

    @classmethod
    def w_open(cls):
        super().w_open()

    @classmethod
    def w_close(cls):
        super().w_close()

    @classmethod
    def w_before_window_begin(cls):
        pass

    @classmethod
    def w_after_window_end(cls):
        pass

    _any_change = False

    @classmethod
    def w_content(cls):
        super().w_content()
        changed, user_settings.base_url = c.input_text("Base URL", user_settings.base_url)
        cls._any_change |= changed
        changed, user_settings.projects_dir = c.file_or_folder_selector("Projects Dir", user_settings.projects_dir)
        cls._any_change |= changed
        changed, user_settings.invalid_project_ids_path = c.file_or_folder_selector("Invalid Project IDs Path", user_settings.invalid_project_ids_path)
        cls._any_change |= changed


        if c.highlighted_button("Save UserSettings"):
            save_user_settings(user_settings)
