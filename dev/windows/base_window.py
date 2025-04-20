import logging
from abc import abstractmethod
from typing import Optional

import imgui
import moderngl

from dev.global_app_state import g
from dev.modules import StyleModule


class BaseWindow:
    config_translation_file_name: str = None  # 用户设置项
    _inited = False

    @classmethod
    @abstractmethod
    def w_init(cls):
        logging.info(f'[{cls.__name__}] init')
        cls._inited = True

    @classmethod
    @abstractmethod
    def w_update(cls):
        pass

    @classmethod
    @abstractmethod
    def w_show(cls, **kwargs):
        pass


class PopupWindow(BaseWindow):
    config_popup_window_name = ''
    config_popup_window_position: Optional[tuple[int, int]] = None
    config_popup_window_size: Optional[tuple[int, int]] = None
    config_popup_window_flags = imgui.WINDOW_NONE

    _opened = False  # 是否打开
    _active = False  # 是否具有焦点
    _position = (0, 0)
    _size = (0, 0)

    @classmethod
    @abstractmethod
    def w_init(cls):
        super().w_init()
        cls.config_popup_window_name = cls.__name__ if cls.config_popup_window_name == '' else cls.config_popup_window_name

        if cls.config_popup_window_position is not None:
            imgui.set_next_window_position(*cls.config_popup_window_position)

        if cls.config_popup_window_size is not None:
            imgui.set_next_window_size(*cls.config_popup_window_size)

    @classmethod
    @abstractmethod
    def w_update(cls):
        pass

    @classmethod
    def w_show(cls, **kwargs):
        """no need to implement"""
        if not cls._opened:
            return
        super().w_show()

        if "flags" in kwargs.keys():
            flags = kwargs["flags"]
        else:
            flags = cls.config_popup_window_flags

        # before window begin
        cls.w_before_window_begin()
        StyleModule.push_loose_padding()
        expanded, opened = imgui.begin(cls.config_popup_window_name, True, flags)
        StyleModule.pop_loose_padding()
        # ==================================================================
        #                           window started
        # ==================================================================
        # update variables
        cls._position = imgui.get_window_position()
        cls._size = imgui.get_window_size()

        cls._active = imgui.is_window_focused(
            imgui.HOVERED_ALLOW_WHEN_BLOCKED_BY_POPUP | imgui.HOVERED_ROOT_AND_CHILD_WINDOWS)

        # show main content
        cls.w_content()

        # endregion

        # ==================================================================
        #                             window end
        # ==================================================================
        imgui.end()

        # after window end
        cls.w_after_window_end()

        # handle close
        if not opened:
            cls.w_close()
            return

    @classmethod
    @abstractmethod
    def w_open(cls):
        cls._opened = True

    @classmethod
    @abstractmethod
    def w_close(cls):
        cls._opened = False

    @classmethod
    def w_before_window_begin(cls):
        pass

    @classmethod
    @abstractmethod
    def w_content(cls):
        pass

    @classmethod
    def w_after_window_end(cls):
        pass

    @classmethod
    def is_opened(cls):
        return cls._opened

    @classmethod
    def is_active(cls):
        return cls._active

    @classmethod
    def get_rect_min(cls) -> tuple[int, int]:
        return cls._position

    @classmethod
    def get_rect_max(cls) -> tuple[int, int]:
        return cls._position[0] + cls._size[0], cls._position[1] + cls._size[1]

    @classmethod
    def _on_blurred_bg_complete(cls, tex: moderngl.Texture):
        """当请求背景图像完成时"""
        cls._bg_tex = tex
        cls._bg_blur_last_update_time = g.mTime

    @classmethod
    def get_size(cls):
        return cls._size

    @classmethod
    def get_position(cls):
        return cls._position
