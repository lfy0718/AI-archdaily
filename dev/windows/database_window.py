# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 3/28/2025 10:47 AM
# @Function:
import logging
import threading
from typing import Callable

import imgui
from tqdm import tqdm

from config import *
from dev.components import c
from dev.global_app_state import g
from dev.windows.base_window import PopupWindow
from utils import db_utils

class DatabaseWindow(PopupWindow):
    _working_context = None
    _working_curr = 0
    _working_total = 1
    _collection_name = "content_collection"
    _skip_exist = True

    @classmethod
    def start_work(cls, ctx_name,  working_content: Callable,total= None, on_complete_callback=None):
        if cls._working_context is not None:
            logging.warning("Another task is running")
            return
        if total is None:
            total = 1
        if total <= 0:
            return
        # prepare
        cls._working_context = ctx_name
        cls._working_total = total
        cls._working_curr = 0
        def _func():
            logging.info(f"{cls._working_context}开始执行")
            # working
            try:
                working_content()
                logging.info(f"{cls._working_context}执行完成")
                cls._working_context = None
                if on_complete_callback:
                    on_complete_callback()
            except Exception as e:
                logging.error(f"{cls._working_context}执行出错：{e}")

        threading.Thread(target=_func).start()
    @classmethod
    def update_work_total(cls, total):
        cls._working_total = total
    @classmethod
    def update_work_progress(cls, count=1):
        cls._working_curr += count

    @classmethod
    def w_init(cls):
        super().w_init()
        cls.w_open()

    @classmethod
    def w_update(cls):
        super().w_update()

    @classmethod
    def w_content(cls):
        super().w_content()
        with imgui.font(g.mFontL):
            c.ctext("Database Tool")

        if imgui.begin_tab_bar("db_steps"):
            cls._imgui_step_tab_item_template("Step1-下载html", "Step1", cls.step1)
            cls._imgui_step_tab_item_template("Step2-解析html", "Step2", cls.step2)
            cls._imgui_step_tab_item_template("Step3-下载图像", "Step3", cls.step3)
            imgui.end_tab_bar()

    @classmethod
    def _imgui_step_tab_item_template(cls, tab_name, context_prefix, step_content: Callable[[], None]) -> None:
        if imgui.begin_tab_item(tab_name).selected:
            if cls._working_context is not None and not cls._working_context.startswith(context_prefix):
                c.info_box("step_error", f"当前正在执行{cls._working_context}任务", "warning")
            else:
                step_content()
            imgui.end_tab_item()
    @classmethod
    def _imgui_connect_db_region(cls):
        if db_utils.is_getting_mongo_client():
            c.info_box("db_connecting", "正在连接数据库...", "info")
        elif g.mMongoClient is None:
            if c.button(f"连接到数据库：{user_settings.mongodb_archdaily_db_name}", width=imgui.get_content_region_available_width()):
                db_utils.get_mongo_client_async(user_settings.mongodb_host, lambda client: setattr(g, "mMongoClient", client))
        else:
            c.info_box("db_connected", f"已连接到：{user_settings.mongodb_archdaily_db_name}", "success", right_button_func=lambda: imgui.open_popup("db_connected_popup"))
        if imgui.begin_popup("db_connected_popup"):
            clicked, _ = imgui.menu_item("取消连接")
            if clicked:
                g.mMongoClient = None
            imgui.end_popup()
    @classmethod
    def step1(cls):
        imgui.text("step1 - 将content.json的数据迁移至云")
        cls._imgui_connect_db_region()
        if not g.mMongoClient:
            return

    @classmethod
    def step2(cls):
        imgui.text('step2')

    @classmethod
    def step3(cls):
        imgui.text("step3")


    @classmethod
    def upload_content_to_db(cls):
        # 连接到MongoDB
        if not g.mMongoClient:
            raise Exception("No MongoClient")
        client = g.mMongoClient
        db = client[user_settings.mongodb_archdaily_db_name]
        content_collection = db[cls._collection_name]
        all_projects = os.listdir(user_settings.projects_dir)
        cls.update_work_total(len(all_projects))

        # 遍历每个项目文件夹
        for project_id in tqdm(all_projects):
            cls.update_work_progress()
            project_path = os.path.join(user_settings.projects_dir, project_id)

            # 检查数据库中是否存在该 _id
            if cls._skip_exist:
                existing_doc = content_collection.find_one({'_id': project_id})
                if existing_doc:
                    # logging.info(f"project: {project_id} 已存在于数据库中，跳过处理")
                    continue

            # 读取content.json
            content_json_path = os.path.join(project_path, 'content.json')
            if not os.path.exists(content_json_path):
                logging.warning(f"project: {project_id} content.json文件不存在")
                continue

            with open(content_json_path, 'r', encoding='utf-8') as f:
                content_data = json.load(f)

            # 插入或更新content数据
            content_doc = {'_id': project_id}
            content_doc.update(content_data)
            content_result = content_collection.update_one(
                {'_id': project_id},
                {'$set': content_doc},
                upsert=True  # 修改为 upsert=True，确保不存在时插入
            )

            # # 区分插入和更新操作
            # if content_result.upserted_id:
            #     logging.info(f"project: {project_id} 插入成功")
            # else:
            #     logging.info(f"project: {project_id} 更新成功，修改计数: {content_result.modified_count}")
