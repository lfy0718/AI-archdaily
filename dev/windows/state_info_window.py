# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 3/28/2025 10:47 AM
# @Function:
import os
import time

import imgui
from config import *
from dev.components import c
from dev.global_app_state import g
from dev.modules import StyleModule
from dev.windows.base_window import PopupWindow


class StateInfoWindow(PopupWindow):
    @classmethod
    def w_init(cls):
        super().w_init()
        cls.w_open()

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

    _max_count = 32

    @classmethod
    def w_content(cls):
        super().w_content()
        imgui.text("状态信息：")
        imgui.text(f"alive workers： {g.mAliveWorkers}")

        c.begin_child("alive projects", height=200 * g.global_scale, bg_color=StyleModule.COLOR_CHILD_BG)
        c.bold_text("这些项目正在工作：")

        imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (1, 1))
        curr_time = time.time()
        for project_id in g.mAliveProjects:
            start_time = g.mProjectStartTimes[project_id]
            if project_id in g.mProjectSubCurr:
                curr = g.mProjectSubCurr[project_id]
                total = g.mProjectSubTotal[project_id]
                sub_progress_str = f"[{curr}/{total}]"
            else:
                sub_progress_str = ""
            project_id: str = project_id
            opened, selected = imgui.selectable(f"{project_id.ljust(10, ' ')} {sub_progress_str.ljust(10, ' ')} {(curr_time - start_time):.0f}s")
            if opened:
                os.startfile(os.path.join(user_settings.projects_dir, project_id))
        imgui.pop_style_var()
        c.end_child()

        imgui.separator()

        c.begin_child("success projects", height=200 * g.global_scale, bg_color=StyleModule.COLOR_CHILD_BG)
        c.bold_text(f"{len(g.mSuccessProjects)}项目被标记为成功：")
        imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (1, 1))
        total = min(len(g.mSuccessProjects), cls._max_count)
        imgui.text(f"前{total}项：")
        for i in range(total):
            project_id = g.mSuccessProjects[-(i + 1)]
            opened, selected = imgui.selectable(f"{project_id}")
            if opened:
                os.startfile(os.path.join(user_settings.projects_dir, project_id))
        imgui.pop_style_var()
        c.end_child()
