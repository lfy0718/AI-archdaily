import logging
from dataclasses import dataclass
from enum import Enum
from typing import Type, Callable

import imgui
import moderngl

from dev.global_app_state import g
from dev.windows.base_window import BaseWindow, PopupWindow
from dev.windows.scraper_window import ScraperWindow
from dev.windows.state_info_window import StateInfoWindow

# NOTE: If you added a new window, import it here.

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# NOTE: If you added a new window, make sure to add it into ALL_WINDOWS list.
ALL_WINDOWS: list[Type[BaseWindow]] = [
    ScraperWindow,
    StateInfoWindow
]

# NOTE: If you added a new popup window, make sure to add it into POPUP_WINDOWS list.
POPUP_WINDOWS: list[Type[PopupWindow]] = [
    ScraperWindow,
    StateInfoWindow
]


class ExcludeTypes(Enum):
    Nothing = 0
    Self = 1
    AllPopups = 2


@dataclass
class CommandForGetBlurBg:
    caller: Type[PopupWindow]
    exclude_type: ExcludeTypes
    callback: Callable[[moderngl.Texture], None] = None


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

    @classmethod
    def w_render(cls):
        with imgui.font(g.mFont):
            for window in ALL_WINDOWS:
                window.w_show()

    @classmethod
    def w_late_update(cls):
        pass
