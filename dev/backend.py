# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/21/2025 3:40 PM
# @Function:
import atexit
import json
import logging
import os
import random
import threading
import time
import traceback
import warnings
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional, Any

import numpy as np
import requests
import streamlit as st
from tqdm import tqdm

from utils import db_utils

logging.info("Backend Reloaded ============================================================")


@st.cache_resource
def load_config():
    # config will only be loaded once during the whole lifetime
    # 也可以让装饰器改为st.cache， 这样每次刷新页面就会重新加载，可以方便调试
    import config
    return config


config = load_config()  # use cached config
user_settings = config.user_settings


class WorkingContext:
    # 自定义的创建工作任务的上下文
    def __init__(self, ctx_name: str,
                 working_content: Callable[['WorkingContext', Any, ...], None],
                 *args,
                 total: Optional[int] = None,
                 on_complete_callback: Callable[[], None] = None,
                 singleton=True,
                 enable_ctx_scope_check=False):

        self._ctx_name = ctx_name
        self._working_content = working_content
        self.args = args
        self._on_complete_callback = on_complete_callback
        self._curr = 0
        self._total = total if total is not None else 1
        self._singleton = singleton
        self._enable_ctx_scope_check = enable_ctx_scope_check
        self._should_stop = False
        self._is_running = False
        self._success = False
        self._msg = ""

        self._success_projects = []
        self._failed_projects = []
        self._running_projects = []
        self._complete_projects = []
        self._project_start_times: dict[str: float] = {}
        self._project_sub_curr: dict[str: int] = {}
        self._project_sub_total: dict[str: int] = {}

        self._custom_data = {}

    def start_work(self) -> None:
        if self._singleton and len(g.running_context) > 0:
            self._msg = f"{self._ctx_name}.singleton set to True and Another tasks is running"
            logging.warning(self._msg)
            return
        if self._enable_ctx_scope_check and not WorkingContext.check_ctx_scope(self._ctx_name):
            self._msg = f"Enable Context Scope Check enabled, but current scope: {self._ctx_name} is not same as last scope: {g.last_context_name}"
            logging.warning(self._msg)
            self._success = False
            return
        if self._total is None or self._total <= 0:
            self._msg = f"{self._ctx_name} total is None or total <= 0"
            logging.warning(self._msg)
            self._success = False
            return
        if self._ctx_name in g.running_context:
            self._msg = f"{self._ctx_name} is already running"
            logging.warning(self._msg)
            self._success = False
            return

        g.running_context[self._ctx_name] = self
        self._is_running = True
        self._should_stop = False
        self._curr = 0
        self._success = False
        self._msg = f"{self._ctx_name} 开始执行"
        logging.info(self._msg)

        def _func():
            time.sleep(0.1)  # 加一个小小的延迟，等待UI更新完毕后再开始
            try:
                # ==========================================================================================
                self._working_content(self, *self.args)  # main content 需要传入ctx参数
                # ==========================================================================================
                if self._on_complete_callback:
                    logging.info(f"{self._ctx_name} 正在执行完成回调函数")
                    self._on_complete_callback()
                self._success = True
                self._msg = f"{self._ctx_name} 完成"
                logging.info(self._msg)
            except Exception as e:
                self._success = False
                self._msg = f"{self._ctx_name} 执行出错, {e}"
                logging.warning(self._msg)
                traceback.print_exc()
            finally:
                g.running_context.pop(self._ctx_name)
                self._is_running = False
                g.last_context_name = self._ctx_name
                logging.info(f"last_context_name已更新为:{g.last_context_name}")

        threading.Thread(target=_func).start()

    def stop_work(self):
        self._should_stop = True  # 标记为停止，并等待线程结束，线程中的循环需要加入对_should_stop的判断
        while self._is_running:
            time.sleep(0.1)

    def get_status(self):
        status = {'is_running': self._is_running, 'success': self._success,
                  'msg': self._msg, 'curr': self._curr, 'total': self._total, 'should_stop': self._should_stop}
        status.update(self.custom_data)
        return status

    # region project related status
    def get_lasting_time(self, project_id):
        if project_id in self._project_start_times:
            return time.time() - self._project_start_times[project_id]
        else:
            return -1

    def get_project_sub_curr(self, project_id):
        if project_id in self._project_sub_curr:
            return self._project_sub_curr[project_id]
        else:
            return -1

    def get_project_sub_total(self, project_id):
        if project_id in self._project_sub_total:
            return self._project_sub_total[project_id]
        else:
            return -1

    def get_project_detail_info_str(self, project_id):
        if project_id in self._running_projects:
            if project_id in self._project_sub_curr and project_id in self._project_sub_total:
                sub_curr = self.get_project_sub_curr(project_id)
                sub_total = self.get_project_sub_total(project_id)
                return f"{project_id} [{sub_curr}/{sub_total}] {int(self.get_lasting_time(project_id))}s"
            else:
                return f"{project_id} {int(self.get_lasting_time(project_id))}s"
        else:
            return f"{project_id} Complete"

    # endregion

    # region put these in working content
    def set_total(self, total):
        self._total = total

    def set_curr(self, value):
        self._curr = value

    def update(self, count=1):
        self._curr += count

    def report_msg(self, msg):
        self._msg = msg
        logging.info(msg)

    def report_project_start(self, project_id):
        """报告项目开始"""
        project_id = str(project_id)
        if project_id in self._running_projects:
            return
        self._running_projects.append(project_id)
        self._project_start_times[project_id] = time.time()

    def _on_project_complete(self, project_id):
        if project_id in self._running_projects:
            self._running_projects.remove(project_id)
        if project_id in self._project_start_times:
            self._project_start_times.pop(project_id)
        if project_id in self._project_sub_total:
            self._project_sub_total.pop(project_id)
        if project_id in self._project_sub_curr:
            self._project_sub_curr.pop(project_id)

    def report_project_complete(self, project_id):
        """报告项目完成"""
        project_id = str(project_id)
        self._complete_projects.append(project_id)
        self._on_project_complete(project_id)

    def report_project_success(self, project_id):
        """报告项目完成并成功"""
        project_id = str(project_id)
        self._success_projects.append(project_id)
        self._complete_projects.append(project_id)
        self._on_project_complete(project_id)

    def report_project_failed(self, project_id):
        """报告项目完成并失败"""
        project_id = str(project_id)
        self._failed_projects.append(project_id)
        self._complete_projects.append(project_id)
        self._on_project_complete(project_id)

    def report_project_sub_total(self, project_id, total):
        project_id = str(project_id)
        self._project_sub_total[project_id] = total

    def report_project_sub_curr(self, project_id, curr):
        project_id = str(project_id)
        self._project_sub_curr[project_id] = curr

    @property
    def custom_data(self):
        return self._custom_data

    @property
    def should_stop(self):
        return self._should_stop

    # endregion

    @property
    def success_projects(self):
        return self._success_projects

    @property
    def failed_projects(self):
        return self._failed_projects

    @property
    def running_projects(self):
        return self._running_projects

    @staticmethod
    def check_ctx_scope(ctx_name):
        ctx_name = ctx_name.replace("_", "-")
        if g.last_context_name != "":
            last_scope = g.last_context_name.split("-")[0]
            curr_scope = ctx_name.split("-")[0]
            if last_scope != curr_scope:
                return False
        return True


class GlobalAppState:
    def __init__(self):
        from utils.html_utils import ArchdailyFlags, GoooodFlags
        self.running_context: dict[str: 'WorkingContext'] = {}
        self.last_context_name = ""
        self.project_id_queue = []

        self.flag_states = {
            "archdaily": {flag.name: False for flag in ArchdailyFlags if flag != ArchdailyFlags.NONE},
            "gooood": {flag.name: False for flag in GoooodFlags if flag != GoooodFlags.NONE}
        }

        self.flag_name_to_flag = {
            "archdaily": {flag.name: flag for flag in ArchdailyFlags},
            "gooood": {flag.name: flag for flag in GoooodFlags}
        }

        # db
        self.mongo_client = None

        atexit.register(self.close_mongo_client)

    def close_mongo_client(self):
        if self.mongo_client is not None:
            logging.info("mongodb client连接已关闭")
            self.mongo_client.close()


@st.cache_resource
def create_global_app_state():
    return GlobalAppState()


g = create_global_app_state()  # this g is shared by all users and only be loaded once


# region UI Templates
def template_flags(flag_type):
    if flag_type not in g.flag_states:
        st.warning(f"flag_states[{flag_type}] not found")
        return

    def on_change(_flag_name: str):
        ss_key_value = st.session_state[f'key_{flag_type}_{_flag_name}']
        st.session_state[f"{flag_type}_{_flag_name}"] = ss_key_value
        g.flag_states[flag_type][_flag_name] = ss_key_value
        logging.info(f"{flag_type}.{_flag_name} set to {ss_key_value}")

    def make_on_change(_flag_name: str):
        # 创建闭包函数
        return lambda: on_change(_flag_name)

    for flag_name in g.flag_states[flag_type]:
        ss_name = f"{flag_type}_{flag_name}"
        if ss_name not in st.session_state:
            st.session_state[ss_name] = g.flag_states[flag_type][flag_name]
        st.checkbox(flag_name, value=st.session_state[ss_name], key=f'key_{flag_type}_{flag_name}', on_change=make_on_change(flag_name))


def template_project_id_queue_info_box(name: str, ctx_name: str):
    if len(g.project_id_queue) == 0:
        st.info(f"没有{name}")
    elif not WorkingContext.check_ctx_scope(ctx_name):
        # st.warning(f"当前project_id_queue的项目为其他{g.last_context_name}, 不适用于当前{ctx_name}")
        pass
    else:
        st.info(f"{name}数量: {len(g.project_id_queue)}")


def template_start_work_with_progress(label, ctx_name, working_content: Callable[['WorkingContext', Any, ...], None],
                                      *args,
                                      ctx_singleton=True, ctx_enable_ctx_scope_check=False,
                                      st_show_detail_number=False, st_show_detail_project_id=False,
                                      st_button_type='primary', st_button_icon=None) -> dict:
    disabled = False
    suffix = ""
    if ctx_enable_ctx_scope_check:
        # pre-check
        if not WorkingContext.check_ctx_scope(ctx_name):
            disabled |= True
            suffix += " ctx_scope unmatch"
    if ctx_name in g.running_context:
        disabled |= True
        suffix += " running"

    if st.button(label + suffix, use_container_width=True, type=st_button_type, key=f"run_{ctx_name}",
                 icon=st_button_icon, disabled=disabled):
        logging.info(f"{ctx_name}按钮被点击")
        ctx = WorkingContext(ctx_name, working_content, *args, singleton=ctx_singleton,
                             enable_ctx_scope_check=ctx_enable_ctx_scope_check)
        ctx.start_work()

    if ctx_name not in g.running_context:
        # st.text(f"{ctx_name}不在运行")
        return {}

    # 下面都是ctx正在运行的代码
    ctx: WorkingContext = g.running_context[ctx_name]
    # region placeholders
    stop_placeholder = st.empty()
    progress_placeholder = st.empty()
    running_projects_placeholder, success_projects_placeholder, failed_projects_placeholder = None, None, None
    running_projects_detail_placeholder, success_projects_detail_placeholder, failed_projects_detail_placeholder = None, None, None

    if st_show_detail_number:
        col1, col2, col3 = st.columns(3)
        running_projects_placeholder = col1.empty()
        success_projects_placeholder = col2.empty()
        failed_projects_placeholder = col3.empty()

        if st_show_detail_project_id:
            expander = col1.expander("View Running Projects", icon="🔥")
            running_projects_detail_placeholder = expander.empty()
            expander = col2.expander("View Success Projects", icon="✅")
            success_projects_detail_placeholder = expander.empty()
            expander = col3.expander("View Failed Projects", icon="❌")
            failed_projects_detail_placeholder = expander.empty()
    # endregion
    if stop_placeholder.button("Stop", use_container_width=True, key="stop_" + ctx_name, disabled=ctx is None):
        logging.warning(f"{ctx_name}正在停止")
        ctx.stop_work()
    while True:
        time.sleep(0.5)
        status = ctx.get_status()
        is_running = status['is_running']
        should_stop = status['should_stop']
        # region these components update every 0.5 seconds
        progress_placeholder.progress(status['curr'] / status['total'], text=f"{status['curr']}/{status['total']}")
        if st_show_detail_number:
            running_projects_placeholder.text(f"运行中: {len(ctx.running_projects)}")
            success_projects_placeholder.text(f"成功: {len(ctx.success_projects)}")
            failed_projects_placeholder.text(f"失败: {len(ctx.failed_projects)}")
            if st_show_detail_project_id:
                running_projects_detail_placeholder.text(
                    '\n'.join([ctx.get_project_detail_info_str(project_id) for project_id in ctx.running_projects]))
                success_projects_detail_placeholder.text('\n'.join(ctx.success_projects[-10:][::-1]))
                failed_projects_detail_placeholder.text('\n'.join(ctx.failed_projects[-10:][::-1]))
        if is_running and should_stop:
            stop_placeholder.text("等待任务完成...")
        # endregion
        if not is_running:
            break

    # 运行完成 ==================================
    # clear placeholders
    stop_placeholder.empty()
    progress_placeholder.empty()
    if status['success']:
        st.success(f"{status['msg']}")
    else:
        st.warning(f"{status['msg']}")
    return status


def template_mongodb_connection_region(db_name, db_name_setter: Callable[[str], None]) -> bool:
    if g.mongo_client is None:
        db_host = st.text_input("MongoDB Host", user_settings.mongodb_host)
        col1, col2 = st.columns(2)
        if col1.button("保存", use_container_width=True):
            user_settings.mongodb_host = db_host
            config.save_user_settings(user_settings)
        if col2.button("保存并连接", use_container_width=True, type="primary"):
            user_settings.mongodb_host = db_host
            config.save_user_settings(user_settings)
            success, g.mongo_client = db_utils.get_mongo_client(db_host)
            if not success:
                st.warning("连接失败")
            else:
                st.rerun()
        return False
    assert g.mongo_client is not None
    db_names = g.mongo_client.list_database_names()
    if db_name not in db_names:
        st.warning(f"无法连接到数据库({db_name})")
        db_name = st.text_input("DB Name", db_name)
        if st.button("保存并刷新"):
            db_name_setter(db_name)
            config.save_user_settings(user_settings)
            logging.info(f"已切换至数据库({db_name})")
            st.rerun()
    else:
        col1, col2 = st.columns([8, 2])
        col1.success(f"🌿已成功连接至数据库 {db_name}")
        if col2.button("断开连接", use_container_width=True):
            g.mongo_client.close()
            g.mongo_client = None
            st.rerun()


# endregion


# region Archdaily Functions
def archdaily__scan_projects_with_no_content_html(ctx: WorkingContext, *args):
    _ = args
    _all_projects = os.listdir(user_settings.archdaily_projects_dir)
    ctx.set_total(len(_all_projects))
    g.project_id_queue = []
    for project_id in _all_projects:
        ctx.report_project_start(project_id)
        if ctx.should_stop:
            break
        ctx.update(1)
        folder_path = os.path.join(user_settings.archdaily_projects_dir, project_id)
        if os.path.isdir(folder_path):
            html_file_path = os.path.join(folder_path, f'content.html')  # 扫描是否有content.html
            if not os.path.exists(html_file_path):
                g.project_id_queue.append(project_id)
        ctx.report_project_success(project_id)


def archdaily__scan_valid_project_id_in_range(ctx: WorkingContext, start_id: int, end_id: int):
    ctx.set_total(4)

    # 从本地文件加载invalid_project_ids
    if os.path.exists(user_settings.archdaily_invalid_projects_ids_path):
        with open(user_settings.archdaily_invalid_projects_ids_path, 'r', encoding='utf-8') as f:
            invalid_project_ids = set(json.load(f))
    else:
        invalid_project_ids = set()
    ctx.set_curr(1)
    id_range = list(range(start_id, end_id + 1)) if start_id <= end_id else list(range(end_id, start_id + 1))
    if start_id > end_id:
        id_range.reverse()
    project_id_queue_full: list[str] = [str(project_id) for project_id in id_range]
    ctx.set_curr(2)
    # 扣除all_projects已经存在的项目
    all_projects_set = set(os.listdir(user_settings.archdaily_projects_dir))
    project_id_queue = [project_id for project_id in project_id_queue_full if
                        project_id not in all_projects_set]
    ctx.set_curr(3)
    # 扣除invalid_project_ids
    project_id_queue = [project_id for project_id in project_id_queue if
                        project_id not in invalid_project_ids]
    ctx.set_curr(4)
    g.project_id_queue = project_id_queue


def archdaily__scan_projects_folder_for_parsing_content(ctx: WorkingContext, skip_exist=False, *args):
    _ = args
    _all_projects = os.listdir(user_settings.archdaily_projects_dir)
    ctx.set_total(len(_all_projects))

    if _all_projects == 0:
        raise Exception("没有找到任何项目")

    ctx.report_msg("正在扫描本地文件...")
    g.project_id_queue = []
    num_projects_with_no_content_html = 0
    for project_id in _all_projects:
        ctx.update(1)
        if ctx.should_stop:
            break
        if skip_exist:
            json_file_path = os.path.join(user_settings.archdaily_projects_dir, project_id, 'content.json')
            if os.path.exists(json_file_path):
                continue
        ctx.report_project_start(project_id)
        html_file_path = os.path.join(user_settings.archdaily_projects_dir, project_id, 'content.html')

        if os.path.exists(html_file_path):
            g.project_id_queue.append(project_id)
        else:
            num_projects_with_no_content_html += 1
        ctx.report_project_success(project_id)
    ctx.custom_data['num_projects_with_no_content_html'] = num_projects_with_no_content_html
    ctx.custom_data['final_msg'] = f"共计{len(_all_projects)}个项目，其中{len(g.project_id_queue)}个项目已添加到队列"


def archdaily__scan_projects_folder_for_downloading_images(ctx: WorkingContext, *args):
    return common__scan_projects_folder_for_downloading_images(ctx, user_settings.archdaily_projects_dir, *args)


def archdaily__download_projects_html_to_local(ctx: WorkingContext, *args):
    from utils.html_utils import request_project_html_archdaily, flush_success_queue
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # 从本地文件加载invalid_project_ids
    if os.path.exists(user_settings.archdaily_invalid_projects_ids_path):
        with open(user_settings.archdaily_invalid_projects_ids_path, 'r', encoding='utf-8') as f:
            invalid_project_ids = set(json.load(f))
    else:
        invalid_project_ids = set()
    _total = len(g.project_id_queue)
    assert _total > 0, "没有项目需要下载"
    ctx.set_total(_total)
    saving_gap = max(_total // 20, 100)  # 总数平均分20份，但是最小每100轮保存一次

    def save_invalid_project_ids():
        with open(user_settings.archdaily_invalid_projects_ids_path, 'w', encoding='utf-8') as f:
            logging.info("保存invalid_project_ids")
            json.dump(list(invalid_project_ids), f, ensure_ascii=False, indent=4)

    def _get_html_content(project_id: str, i: int):
        if ctx.should_stop:
            return
        ctx.report_project_start(project_id)
        success = request_project_html_archdaily(project_id, i, _total, invalid_project_ids,
                                                 force_update=False)
        if success is True:
            ctx.report_project_success(project_id)
        elif success is False:
            ctx.report_project_failed(project_id)
        else:
            ctx.report_project_complete(project_id)
        ctx.update(1)
        if i % saving_gap == 0:
            save_invalid_project_ids()

    with ThreadPoolExecutor(max_workers=32) as executor:
        futures = (executor.submit(_get_html_content, project_id, i) for i, project_id in
                   enumerate(g.project_id_queue))
        for future in as_completed(futures):
            future.result()

    flush_success_queue('content_html')
    save_invalid_project_ids()


def archdaily__parse_htmls(ctx: WorkingContext, flags_state, *args):
    from utils.html_utils import parse_project_content_archdaily, flush_success_queue, ArchdailyFlags
    from concurrent.futures import ThreadPoolExecutor, as_completed

    _total = len(g.project_id_queue)
    assert _total > 0, "没有项目需要解析"

    ctx.set_total(_total)

    # get flags
    combined_flags = ArchdailyFlags.NONE
    for flag_name, value in flags_state.items():
        if value:
            logging.info(f"{flag_name} is On")
            flag = g.flag_name_to_flag['archdaily'][flag_name]
            combined_flags |= flag

    def _parse_project_content(project_id: str, i: int):
        if ctx.should_stop:
            return
        time.sleep(0.02)

        ctx.report_project_start(project_id)

        changed = parse_project_content_archdaily(project_id, i, _total, flags=combined_flags)
        if changed is True:
            ctx.report_project_success(project_id)
        elif changed is False:
            ctx.report_project_failed(project_id)
        else:
            ctx.report_project_complete(project_id)

        ctx.update(1)

    with ThreadPoolExecutor(max_workers=64) as executor:
        # 注意括号，使用Generator而非List
        futures = (executor.submit(_parse_project_content, project_id, i) for i, project_id in
                   enumerate(g.project_id_queue))
        logging.info("开始解析页面内容... 如果遇到image_gallery为空的情况，可能需要等待返回image_gallery结果")
        for future in tqdm(as_completed(futures), total=len(g.project_id_queue)):
            future.result()

    flush_success_queue('content_json')


def archdaily__download_gallery_images(ctx: WorkingContext, *args):
    return common__download_gallery_images(ctx, user_settings.archdaily_projects_dir, *args)


def archdaily__upload_content(ctx: WorkingContext, skip_exist: bool = True, *args):
    return common__upload_content(ctx, user_settings.mongodb_archdaily_db_name, user_settings.archdaily_projects_dir, skip_exist, *args)


def archdaily__scan_embedding_db(ctx: WorkingContext, skip_exist: bool = True, *args):
    return common__scan_embedding_db(ctx, user_settings.mongodb_archdaily_db_name, user_settings.archdaily_projects_dir, skip_exist, *args)


def archdaily__calculate_text_embedding_using_multimodal_embedding_v1_api(ctx: WorkingContext,
                                                                          chunk_size=500,
                                                                          chunk_overlap=50,
                                                                          *args):
    return common__calculate_text_embedding_using_multimodal_embedding_v1_api(ctx, user_settings.mongodb_archdaily_db_name,
                                                                              chunk_size, chunk_overlap, *args)


def archdaily__calculate_text_embedding_using_gme_Qwen2_VL_2B_api(ctx: WorkingContext,
                                                                  chunk_size=500,
                                                                  chunk_overlap=50,
                                                                  *args):
    return common__calculate_text_embedding_using_gme_Qwen2_VL_2B_api(ctx, user_settings.mongodb_archdaily_db_name,
                                                                      chunk_size, chunk_overlap, *args)


# endregion


# region gooood
def gooood__scrap_pages(ctx: WorkingContext, scrap_all=False, start_page=1, end_page=1, skip_exist=False, *args):
    if start_page > end_page:
        start_page, end_page = end_page, start_page
    if scrap_all:
        start_page = 1
    if not scrap_all:
        ctx.set_total(end_page - start_page + 1)
    else:
        ctx.set_total(1)
    page = start_page - 1
    page_count = 0
    pages_folder = os.path.join(user_settings.gooood_results_dir, "pages")
    os.makedirs(pages_folder, exist_ok=True)
    while True:
        page += 1

        if ctx.should_stop:
            break
        if not scrap_all and page > end_page:
            ctx.report_msg("已到达指定页数")
            logging.info(f"已到达指定页数")
            break
        page_count += 1
        ctx.update(1)
        if scrap_all:
            ctx.set_total(page_count + 1)
        json_path = os.path.join(pages_folder, f"page_{str(page).zfill(5)}.json")
        if skip_exist and os.path.exists(json_path):
            continue

        ctx.report_project_start(page)
        try:
            # Send a GET request to the website
            url = user_settings.gooood_base_url.replace("<page>", str(page))
            response = requests.get(url, headers=user_settings.headers)
            if response.status_code != 200:
                ctx.report_project_failed(page)
                continue
            data = json.loads(response.text)
            if len(data) == 0:
                logging.info(f"已到达最后一页")
                ctx.report_project_complete(page)
                break
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False, indent=4))
            ctx.report_project_success(page)
        except requests.exceptions.RequestException as e:
            print(f"Error accessing the website: {e}")
            ctx.report_project_failed(page)
        except Exception as e:
            print(f"An error occurred: {e}")
            ctx.report_project_failed(page)


def gooood__init_projects(ctx: WorkingContext, skip_exist=True, *args):
    pages_folder = os.path.join(user_settings.gooood_results_dir, "pages")
    if not os.path.exists(pages_folder):
        raise Exception("pages文件夹不存在")
    all_pages = os.listdir(pages_folder)
    if not all_pages:
        raise Exception("pages文件夹为空")
    ctx.set_total(len(all_pages))
    for page in tqdm(all_pages):
        ctx.update(1)
        page_path = os.path.join(pages_folder, page)
        with open(page_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for project_data in data:
            project_id = str(project_data['id'])
            project_folder = os.path.join(user_settings.gooood_projects_dir, project_id)
            project_data_path = os.path.join(project_folder, f"{project_id}.json")
            if skip_exist and os.path.exists(project_data_path):
                continue
            os.makedirs(project_folder, exist_ok=True)
            with open(project_data_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(project_data, ensure_ascii=False, indent=4))


def gooood__parse_projects(ctx: WorkingContext, flags_state, skip_exist=False, *args):
    from utils.html_utils import parse_project_content_gooood, flush_success_queue, GoooodFlags
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # get flags
    combined_flags = GoooodFlags.NONE
    for flag_name, value in flags_state.items():
        if value:
            logging.info(f"{flag_name} is On")
            flag = g.flag_name_to_flag['gooood'][flag_name]
            combined_flags |= flag
    if not os.path.exists(user_settings.gooood_projects_dir):
        raise Exception("projects文件夹不存在")

    all_projects = os.listdir(user_settings.gooood_projects_dir)
    if not all_projects:
        raise Exception("projects文件夹为空")
    _total = len(all_projects)
    ctx.set_total(_total)

    def _parse_project_content(project_id: str, i: int):
        if ctx.should_stop:
            return
        time.sleep(0.1)
        ctx.update(1)
        project_data_path = os.path.join(user_settings.gooood_projects_dir, project_id, f"{project_id}.json")
        project_content_path = os.path.join(user_settings.gooood_projects_dir, project_id, f"content.json")
        if skip_exist and os.path.exists(project_content_path):
            return
        ctx.report_project_start(project_id)
        changed = parse_project_content_gooood(project_id, i, _total, flags=combined_flags)
        if changed is True:
            ctx.report_project_success(project_id)
        elif changed is False:
            ctx.report_project_failed(project_id)
        else:
            ctx.report_project_complete(project_id)

    with ThreadPoolExecutor(max_workers=64) as executor:
        futures = (executor.submit(_parse_project_content, project_id, i) for i, project_id in
                   enumerate(all_projects))
        for future in tqdm(as_completed(futures), total=len(all_projects)):
            future.result()

    flush_success_queue('content_json')


def gooood__scan_projects_folder_for_downloading_images(ctx: WorkingContext, *args):
    return common__scan_projects_folder_for_downloading_images(ctx, user_settings.gooood_projects_dir, *args)


def gooood__download_gallery_images(ctx: WorkingContext, *args):
    return common__download_gallery_images(ctx, user_settings.gooood_projects_dir, *args)



def gooood__upload_content(ctx: WorkingContext, skip_exist: bool = True, *args):
    return common__upload_content(ctx, user_settings.mongodb_gooood_db_name, user_settings.gooood_projects_dir, skip_exist, *args)


def gooood__scan_embedding_db(ctx: WorkingContext, skip_exist: bool = True, *args):
    return common__scan_embedding_db(ctx, user_settings.mongodb_gooood_db_name, user_settings.gooood_projects_dir, skip_exist, *args)


def gooood__calculate_text_embedding_using_multimodal_embedding_v1_api(ctx: WorkingContext,
                                                                          chunk_size=500,
                                                                          chunk_overlap=50,
                                                                          *args):
    return common__calculate_text_embedding_using_multimodal_embedding_v1_api(ctx, user_settings.mongodb_gooood_db_name,
                                                                              chunk_size, chunk_overlap, *args)


def gooood__calculate_text_embedding_using_gme_Qwen2_VL_2B_api(ctx: WorkingContext,
                                                                  chunk_size=500,
                                                                  chunk_overlap=50,
                                                                  *args):
    return common__calculate_text_embedding_using_gme_Qwen2_VL_2B_api(ctx, user_settings.mongodb_gooood_db_name,
                                                                      chunk_size, chunk_overlap, *args)
# endregion


# region common
def common__scan_projects_folder_for_downloading_images(ctx: WorkingContext, projects_dir, *args):
    _all_projects = os.listdir(projects_dir)
    if _all_projects == 0:
        raise Exception("没有找到任何项目")

    ctx.set_total(len(_all_projects))

    content_not_exist_count = 0
    g.project_id_queue = []

    # 遍历项目目录下的所有子文件夹
    for folder_name in tqdm(_all_projects):
        if ctx.should_stop:
            break
        ctx.update(1)
        folder_path = os.path.join(projects_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue
        json_file_path = os.path.join(folder_path, 'content.json')
        if not os.path.exists(json_file_path):
            content_not_exist_count += 1  # content.json does not exist, add to content_not_exist_count
            continue
        image_gallery_folder = os.path.join(folder_path, 'image_gallery', 'large')
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        image_gallery_images = data.get('image_gallery', [])
        if not image_gallery_images:
            continue
        if not os.path.exists(image_gallery_folder):
            g.project_id_queue.append(folder_name)
            continue
        image_gallery_names = os.listdir(image_gallery_folder)
        if len(image_gallery_names) < len(image_gallery_images):
            g.project_id_queue.append(folder_name)

    ctx.custom_data[
        'final_msg'] = f"已扫描{len(_all_projects)}个项目，其中{content_not_exist_count}个项目没有content.json文件，{len(g.project_id_queue)}个项目需要下载图像"


def common__download_gallery_images(ctx: WorkingContext, projects_dir, *args):
    from utils.html_utils import download_images_common
    from concurrent.futures import ThreadPoolExecutor, as_completed
    _total = len(g.project_id_queue)
    assert _total > 0, "没有需要下载图像的项目"
    ctx.set_total(_total)

    def _on_img_index_change(project_id, img_index, img_total):
        ctx.report_project_sub_curr(project_id, img_index)
        ctx.report_project_sub_total(project_id, img_total)

    def _download_images(project_id: str, i: int):
        if ctx.should_stop:
            return

        ctx.report_project_start(project_id)
        success = download_images_common(projects_dir, project_id, i, _total, 'large',
                                         img_index_change_callback=_on_img_index_change)
        if success is True:
            ctx.report_project_success(project_id)
        elif success is False:
            ctx.report_project_failed(project_id)
        else:
            ctx.report_project_complete(project_id)
        ctx.update(1)

    with ThreadPoolExecutor(max_workers=48) as executor:
        futures = (executor.submit(_download_images, project_id, i) for i, project_id in enumerate(g.project_id_queue))
        for future in as_completed(futures):
            future.result()

    logging.info('complete')


def common__upload_content(ctx: WorkingContext, db_name, projects_dir, skip_exist: bool = True, *args):
    if g.mongo_client is None:
        raise Exception("MongoDB连接失败")
    db = g.mongo_client[db_name]

    content_collection = db['content_collection']

    all_projects = os.listdir(projects_dir)
    ctx.set_total(len(all_projects))

    def _handle_project(project_id: str):
        if ctx.should_stop:
            return
        ctx.report_project_start(project_id)
        ctx.update(1)
        project_path = os.path.join(projects_dir, project_id)

        # 检查数据库中是否存在该 _id
        if skip_exist:
            existing_doc = content_collection.find_one({'_id': project_id})
            if existing_doc:
                # logging.info(f"project: {project_id} 已存在于数据库中，跳过处理")
                ctx.report_project_complete(project_id)
                return

        # 读取content.json
        content_json_path = os.path.join(project_path, 'content.json')
        if not os.path.exists(content_json_path):
            logging.warning(f"project: {project_id} content.json文件不存在")
            ctx.report_project_failed(project_id)
            return

        try:
            with open(content_json_path, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
        except Exception as e:
            logging.error(f"project: {project_id} content.json文件读取失败，错误信息：{str(e)}")
            os.remove(content_json_path)
            ctx.report_project_failed(project_id)
            return
        # 插入或更新content数据
        content_doc = {'_id': project_id}
        content_doc.update(content_data)
        content_result = content_collection.update_one(
            {'_id': project_id},
            {'$set': content_doc},
            upsert=True  # 修改为 upsert=True，确保不存在时插入
        )
        # 区分插入和更新操作
        # if content_result.upserted_id:
        #     logging.info(f"project: {project_id} 插入成功")
        # else:
        #     logging.info(f"project: {project_id} 更新成功，修改计数: {content_result.modified_count}")
        ctx.report_project_success(project_id)

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = (executor.submit(_handle_project, project_id) for project_id in all_projects)
        for future in tqdm(as_completed(futures), total=len(all_projects)):
            future.result()
    logging.info('complete')


def common__scan_embedding_db(ctx: WorkingContext, db_name, projects_dir, skip_exist: bool = True, *args):
    if g.mongo_client is None:
        raise Exception("MongoDB连接失败")
    db = g.mongo_client[db_name]
    content_collection = db['content_collection']
    content_embedding_collection = db['content_embedding']

    # 遍历每个项目
    all_projects = os.listdir(projects_dir)
    ctx.set_total(len(all_projects))
    g.project_id_queue.clear()
    for project_id in tqdm(all_projects):
        if ctx.should_stop:
            break
        ctx.update(1)
        ctx.report_project_start(project_id)
        # 判断当前 project_id 是否已存在于 content_embedding_collection 中
        existing = content_embedding_collection.find_one(
            {"project_id": project_id},
            {"_id": 1},  # 只返回_id字段
            limit=1
        )
        existing_embeddings = existing is not None
        # 根据用户选项决定是否跳过或覆盖
        if existing_embeddings:
            # 如果embedding数据库中存在当前项目，则根据用户选项决定是否跳过或覆盖
            if skip_exist:
                # logging.info(f"project: {project_id} 已存在于 content_embedding_collection 中，跳过处理")
                ctx.report_project_complete(project_id)
                continue
            else:
                # 删除所有与当前 project_id 相关的文档
                content_embedding_collection.delete_many({'project_id': project_id})
                logging.info(f"project: {project_id} 已存在于 content_embedding_collection 中，删除现有数据并重新处理")
                g.project_id_queue.append(project_id)
                ctx.report_project_success(project_id)
                continue
        # 如果项目在embedding数据库中不存在，则继续处理
        # 从content_collection中提取main_content
        content_doc = content_collection.find_one({'_id': project_id})
        if not content_doc:
            # 项目在数据库中不存在，跳过处理
            ctx.report_project_complete(project_id)
            continue
        if 'main_content' not in content_doc:
            # 如果项目在数据库中没有main_content字段，则跳过处理并警告
            logging.warning(f"project: {project_id} 没有main_content字段")
            ctx.report_project_failed(project_id)
            continue
        # 如果embedding中不存在project 并且 content_collection中存在，则正常添加到队列
        g.project_id_queue.append(project_id)
        ctx.report_project_success(project_id)


def common__calculate_text_embedding_using_multimodal_embedding_v1_api(ctx: WorkingContext, db_name,
                                                                       chunk_size=500,
                                                                       chunk_overlap=50,
                                                                       *args):
    warnings.warn(
        "calculate_text_embedding_using_multimodal_embedding_v1_api 已弃用",
        DeprecationWarning,
        stacklevel=2
    )
    _total = len(g.project_id_queue)
    assert _total > 0, "没有需要处理的项目"
    ctx.set_total(_total)

    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from apis.multimodal_embedding_v1_api import embed_text
    if g.mongo_client is None:
        raise Exception("MongoDB连接失败")
    db = g.mongo_client[db_name]
    content_collection = db['content_collection']
    content_embedding_collection = db['content_embedding']

    # 初始化文本分割器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,  # 每段最大长度
        chunk_overlap=chunk_overlap  # 段与段之间的重叠长度
    )
    valid_api_keys = user_settings.api_keys.copy()

    def _handle_project(project_id: str, i: int):
        if ctx.should_stop:
            return
        ctx.update(1)
        ctx.report_project_start(project_id)

        content_doc = content_collection.find_one({'_id': project_id})
        main_content = content_doc['main_content']

        text_contents = [item['content'] for item in main_content if item['type'] == 'text']
        chunks: list[dict[str: any]] = []
        for text_idx, text in enumerate(text_contents):
            chunks.extend([{'text_idx': text_idx, 'chunk_idx': chunk_idx, 'content': chunk} for chunk_idx, chunk in
                           enumerate(text_splitter.split_text(text))])

        api_key = valid_api_keys.pop(0)  # 拿取api key
        query_chunks = chunks.copy()
        ctx.report_project_sub_total(project_id, len(chunks))
        sub_curr = 0
        for attempt in range(5):  # 最多尝试5次
            curr_chunks = query_chunks.copy()
            query_chunks = []
            for chunk_data in curr_chunks:

                text_idx = chunk_data['text_idx']
                chunk_idx = chunk_data['chunk_idx']
                content = chunk_data['content']
                # 获取嵌入向量
                embedding_vector, status_code = embed_text(content, api_key=api_key)
                if embedding_vector is None:
                    query_chunks.append(chunk_data)
                else:
                    # 插入到content_embedding集合
                    embedding_doc = {
                        'project_id': project_id,
                        'embedding': embedding_vector,
                        'text_content': content,
                        'text_idx': text_idx,
                        'chunk_idx': chunk_idx
                    }
                    result = content_embedding_collection.insert_one(embedding_doc)
                    sub_curr += 1
                    ctx.report_project_sub_curr(project_id, sub_curr)
            if not query_chunks:
                break  # 如果没有失败的chunk，跳出重试循环
            logging.info(f"project: {project_id} 第{attempt + 1}/5次尝试，剩余失败chunk数: {len(query_chunks)}")
        valid_api_keys.append(api_key)  # 返还apikey

        if not query_chunks:
            ctx.report_project_success(project_id)
        else:
            ctx.report_project_failed(project_id)
            logging.warning(f"project: {project_id} 有{len(query_chunks)}个chunk未能成功获取嵌入向量")

    with ThreadPoolExecutor(max_workers=len(user_settings.api_keys)) as executor:
        futures = (executor.submit(_handle_project, project_id, i) for i, project_id in enumerate(g.project_id_queue))
        for future in as_completed(futures):
            future.result()


def common__calculate_text_embedding_using_gme_Qwen2_VL_2B_api(ctx: WorkingContext, db_name,
                                                               chunk_size=500,
                                                               chunk_overlap=50,
                                                               *args):
    _total = len(g.project_id_queue)
    assert _total > 0, "没有项目需要下载"
    ctx.set_total(_total)

    if g.mongo_client is None:
        raise Exception("MongoDB连接失败")
    db = g.mongo_client[db_name]
    content_collection = db['content_collection']
    content_embedding_collection = db['content_embedding']

    ctx.report_msg("正在加载模型...")
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from apis.gme_Qwen2_vl_2B_api import get_text_embeddings

    # 初始化文本分割器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,  # 每段最大长度
        chunk_overlap=chunk_overlap  # 段与段之间的重叠长度
    )
    project_id_queue = deque(g.project_id_queue)
    _doc_buffer_queue = deque()
    _embedding_complete = False

    def _embedding_thread():
        while len(project_id_queue) > 0:
            if ctx.should_stop:
                project_id_queue.clear()
                break
            if len(_doc_buffer_queue) > 100:  # put up to 50 projects in queue
                time.sleep(0.2)
                continue
            project_id = project_id_queue.popleft()
            ctx.update(1)
            ctx.report_project_start(project_id)
            # 此前scan时已经确保都是存在id和maincontent的，因此此处可以直接取用
            content_doc = content_collection.find_one({'_id': project_id})
            main_content = content_doc['main_content']
            text_contents = [item['content'] for item in main_content if item['type'] == 'text']
            chunks: list[dict[str: any]] = []
            for text_idx, text in enumerate(text_contents):
                chunks.extend([{'text_idx': text_idx, 'chunk_idx': chunk_idx, 'content': chunk} for chunk_idx, chunk in
                               enumerate(text_splitter.split_text(text))])
            chunks = [chunk for chunk in chunks if chunk['content'].strip() != '']
            if len(chunks) == 0:
                ctx.report_project_failed(project_id)
                logging.warning(f"project: {project_id} 没有文本内容")
                continue
            ctx.report_project_sub_total(project_id, len(chunks))
            input_texts = [chunk['content'] for chunk in chunks]

            ctx.report_project_sub_curr(project_id, "EBD")
            embedding_vectors = get_text_embeddings(input_texts, batch_size=min(len(input_texts), 32),
                                                    show_progress_bar=False)
            # 判断是否有NaN
            if np.isnan(embedding_vectors).any():
                ctx.report_project_failed(project_id)
                logging.error(f"project: {project_id} 有NaN值 embedding_vectors")
                continue
            buffer = []
            for i, chunk_data in enumerate(chunks):
                text_idx = chunk_data['text_idx']
                chunk_idx = chunk_data['chunk_idx']
                content = chunk_data['content']
                embedding_vector = embedding_vectors[i].tolist()
                embedding_doc = {
                    'project_id': project_id,
                    'chunk_id': f'{project_id}-{text_idx}-{chunk_idx}',
                    'embedding': embedding_vector,
                    'text_content': content,
                    'text_idx': text_idx,
                    'chunk_idx': chunk_idx,
                }
                buffer.append(embedding_doc)
            if len(buffer) == 0:
                ctx.report_project_failed(project_id)
                logging.warning(f"project: {project_id} 没有任何数据")
                continue
            _doc_buffer_queue.append(buffer)
            ctx.report_project_sub_curr(project_id, "InQ")
    def _upload_doc_thread():
        time.sleep(random.random())
        while True:
            if len(_doc_buffer_queue) == 0:
                if len(project_id_queue) > 0:
                    time.sleep(0.2)  # 等待project_id_queue队列为空，再退出循环， 否则一直待命
                    continue
                else:
                    break
            try:
                buffer = _doc_buffer_queue.popleft()
            except Exception as e:
                logging.warning(f"_upload_doc_thread error: {e}, this is not supposed to happen")
                continue
            project_id = buffer[0]['project_id']
            ctx.report_project_sub_curr(project_id, f"WDB")
            result = content_embedding_collection.insert_many(buffer)
            ctx.report_project_success(project_id)


    embedding_thread = threading.Thread(target=_embedding_thread)
    embedding_thread.start()
    upload_thread = threading.Thread(target=_upload_doc_thread)
    upload_thread.start()
    # 等待任务完成
    embedding_thread.join()
    upload_thread.join()

    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def common__fix_nan_embeddings_using_gme_Qwen2_VL_2B_api(ctx: WorkingContext, db_name):
    if g.mongo_client is None:
        raise Exception("MongoDB连接失败")
    db = g.mongo_client[db_name]
    content_embedding_collection = db['content_embedding']
    logging.info("counting documents")
    document_count = content_embedding_collection.count_documents({})
    logging.info(f"document count = {document_count}")
    cursor = content_embedding_collection.find({})
    from apis.gme_Qwen2_vl_2B_api import get_text_embeddings
    modified_count = 0
    ctx.set_total(document_count)
    for doc in tqdm(cursor, total=document_count):
        if ctx.should_stop:
            break
        ctx.update(1)
        assert 'project_id' in doc, "遇到严重错误：文档缺少project_id字段"
        if "embedding" not in doc:
            logging.error(f"one doc of project: {doc['project_id']} has not embedding")
            continue
        if 'text_content' not in doc:
            logging.error(f"one doc of project: {doc['project_id']} has not text_content")
            continue
        embedding = doc["embedding"]
        # 检查embedding是否为列表
        if not isinstance(embedding, list):
            logging.error(f"find one document:{doc['project_id']} has no list embedding")
            continue

        # 新增：检查embedding中是否存在NaN值
        if np.isnan(np.array(embedding)).any():
            ctx.report_project_start(doc['project_id'])
            logging.info(f"find one document:{doc['project_id']} with NaN")
            text_content = doc['text_content']
            embedding_vectors = get_text_embeddings(text_content, batch_size=1,
                                                    show_progress_bar=False)
            new_embedding = embedding_vectors[0].tolist()
            doc.update({"embedding": new_embedding})
            content_embedding_collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"embedding": new_embedding}}
            )
            modified_count += 1
            ctx.report_project_success(doc['project_id'])

# endregion
