import logging
from dataclasses import dataclass
from enum import Enum
from typing import Type, Callable

import imgui
import moderngl

from dev.global_app_state import g
from dev.windows.base_window import BaseWindow, PopupWindow
from dev.windows.scraper_window import ScraperWindow
from dev.windows.database_window import DatabaseWindow
from dev.windows.state_info_window import StateInfoWindow
from dev.windows.settings_window import SettingsWindow
from dev.windows.toast_window import ToastWindow

# NOTE: If you added a new window, import it here.

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# NOTE: If you added a new window, make sure to add it into ALL_WINDOWS list.
ALL_WINDOWS: list[Type[BaseWindow]] = [
    ScraperWindow,
    DatabaseWindow,
    StateInfoWindow,
    SettingsWindow,
    ToastWindow,
]

# NOTE: If you added a new popup window, make sure to add it into POPUP_WINDOWS list.
POPUP_WINDOWS: list[Type[PopupWindow]] = [
    ScraperWindow,
    DatabaseWindow,
    StateInfoWindow,
    SettingsWindow,
    ToastWindow,
]


class ExcludeTypes(Enum):
    Nothing = 0
    Self = 1
    AllPopups = 2


class WindowManager:
    @classmethod
    def w_init(cls):
        logger.info(f"[{cls.__name__}] init")
        g.mWindowManager = cls

        # # NOTE: Init All Windows. If your added new windows, make sure to add it into ALL_WINDOWS list.
        for window in ALL_WINDOWS:
            window.w_init()

    @classmethod
    def w_update(cls):
        for window in ALL_WINDOWS:
            window.w_update()

    _show_imgui_demo_window = False
    @classmethod
    def w_render(cls):
        if imgui.begin_main_menu_bar().opened:
            # first menu dropdown
            if imgui.begin_menu('File', True).opened:
                imgui.menu_item('New', 'Ctrl+N', False, True)
                imgui.menu_item('Open ...', 'Ctrl+O', False, True)

                # submenu
                if imgui.begin_menu('Open Recent', True).opened:
                    imgui.menu_item('doc.txt', None, False, True)
                    imgui.end_menu()

                imgui.end_menu()
            if imgui.begin_menu("Windows", True).opened:
                for window in ALL_WINDOWS:
                    if issubclass(window, PopupWindow):
                        clicked, state = imgui.menu_item(window.__name__, None, window.is_opened(), True)
                        if clicked:
                            if state:
                                window.w_open()
                            else:
                                window.w_close()
                    else:
                        imgui.menu_item(window.__name__, None, True, False)
                _, cls._show_imgui_demo_window = imgui.menu_item("ImGui Demo Window", None, cls._show_imgui_demo_window, True)
                imgui.end_menu()
            imgui.end_main_menu_bar()

        with imgui.font(g.mFont):
            for window in ALL_WINDOWS:
                window.w_show()

        if cls._show_imgui_demo_window:
            imgui.show_demo_window()

    @classmethod
    def w_late_update(cls):
        pass
