import imgui

from config import *
from dev.components import c
from dev.global_app_state import g
from dev.windows.base_window import PopupWindow
from utils import db_utils


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
        changed, user_settings.global_scale = imgui.input_float("Global Scale", user_settings.global_scale)
        user_settings.global_scale = min(max(0.5, user_settings.global_scale), 2.0)
        c.gray_text("该选项重启后生效")
        cls._any_change |= changed

        imgui.separator()

        changed, user_settings.base_url = c.input_text("Base URL", user_settings.base_url)
        cls._any_change |= changed
        changed, user_settings.projects_dir = c.file_or_folder_selector("Projects Dir", user_settings.projects_dir)
        cls._any_change |= changed
        changed, user_settings.invalid_project_ids_path = c.file_or_folder_selector("Invalid Project IDs Path", user_settings.invalid_project_ids_path)
        cls._any_change |= changed

        changed, user_settings.api_keys = c.input_text("API Key", user_settings.api_keys)
        cls._any_change |= changed

        imgui.separator()

        imgui.text("MongoDB")
        changed, user_settings.mongodb_host = c.input_text("MongoDB Host", user_settings.mongodb_host)
        cls._any_change |= changed
        if changed:
            g.mMongoClient = None
        # changed, user_settings.mongodb_db_name = c.input_text("MongoDB DB Name", user_settings.mongodb_db_name)
        # cls._any_change |= changed
        # if changed:
        #     g.mMongoClient = None
        if db_utils.is_getting_mongo_client():
            c.info_box("db_connecting", "正在连接数据库...", "info")
        elif g.mMongoClient is None:
            if c.button("Test Connection"):
                db_utils.get_mongo_client_async(user_settings.mongodb_host, lambda client: setattr(g, "mMongoClient", client))
        else:
            c.info_box("db_connected", "数据库连接成功", "success", right_button_func=lambda: imgui.open_popup("db_connected_popup"))
        if imgui.begin_popup("db_connected_popup"):
            clicked, _ = imgui.menu_item("取消连接")
            if clicked:
                g.mMongoClient = None
            imgui.end_popup()
        if c.highlighted_button("Save UserSettings", disabled=not cls._any_change, width=imgui.get_content_region_available_width()):
            save_user_settings(user_settings)
            cls._any_change = False
