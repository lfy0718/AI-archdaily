# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/20/2025 3:14 PM
# @Function:


import imgui

from dev.components import c
from dev.global_app_state import g
from dev.windows.base_window import PopupWindow


class ToastWindow(PopupWindow):
    config_popup_window_name = 'ToastWindow'
    config_popup_window_flags = imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_DECORATION | imgui.WINDOW_NO_NAV_FOCUS | imgui.WINDOW_ALWAYS_AUTO_RESIZE | imgui.WINDOW_NO_BACKGROUND
    config_popup_window_no_shadow = True

    @classmethod
    def w_init(cls):
        super().w_init()
        cls.w_open()

    @classmethod
    def w_update(cls):
        super().w_update()
        c.Toast.update_toasts()

    @classmethod
    def w_open(cls):
        super().w_open()

    @classmethod
    def w_close(cls):
        super().w_close()

    @classmethod
    def w_before_window_begin(cls):
        imgui.set_next_window_position(g.mWindowSize[0] - 200 * g.global_scale, imgui.get_frame_height_with_spacing())
        imgui.set_next_window_size(200 * g.global_scale, 0)
        # imgui.set_next_window_focus()

    @classmethod
    def w_content(cls):
        super().w_content()
        c.Toast.show_toasts()
