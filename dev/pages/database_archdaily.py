# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/21/2025 4:35 PM
# @Function:
import logging

import streamlit as st
from config import *
from dev import backend as b

def main():
    st.markdown("# Archdaily 数据库管理")
    _step0_connect_to_db()
    tab1, tab2, tab3 = st.tabs(["Step1-上传content", "Step2-计算嵌入向量", "Step3-测试"])
    with tab1:
        _step1_upload_content()
    with tab2:
        _step2_calculating_embedding()
    with tab3:
        _step3_testing()

def _step0_connect_to_db():
    from utils import db_utils
    if b.g.mongo_client is None:
        db_host = st.text_input("MongoDB Host",user_settings.mongodb_host)
        col1, col2 = st.columns(2)
        if col1.button("保存", use_container_width=True):
            user_settings.mongodb_host = db_host
        if col2.button("保存并连接", use_container_width=True, type="primary"):
            user_settings.mongodb_host = db_host
            success, b.g.mongo_client = db_utils.get_mongo_client(db_host)
            if not success:
                st.warning("连接失败")
            else:
                st.rerun()
        return
    assert b.g.mongo_client is not None
    db_names = b.g.mongo_client.list_database_names()
    if user_settings.mongodb_archdaily_db_name not in db_names:
        st.warning(f"无法连接到数据库({user_settings.mongodb_archdaily_db_name})")
        db_name = st.text_input("DB Name", user_settings.mongodb_archdaily_db_name)
        if st.button("保存并刷新"):
            user_settings.mongodb_archdaily_db_name = db_name
            logging.info(f"已切换至数据库({user_settings.mongodb_archdaily_db_name})")
            st.rerun()
    else:
        col1, col2 = st.columns([8, 2])
        col1.success(f"🌿已成功连接至数据库 {user_settings.mongodb_archdaily_db_name}")
        if col2.button("断开连接", use_container_width=True):
            b.g.mongo_client.close()
            b.g.mongo_client = None
            st.rerun()
def _step1_upload_content():
    skip_exist = st.checkbox("跳过已存在的项目", key="DBStep1-upload")
    b.template_start_work_with_progress("上传项目", "DBStep1-upload",
                                        b.upload_content, skip_exist,
                                        st_show_detail_number=True, st_show_detail_project_id=True, st_button_icon="✨",)


def _step2_calculating_embedding():
    skip_exist = st.checkbox("跳过已存在的项目", key="DBStep2-calculate")
    b.template_start_work_with_progress("计算嵌入向量", "DBStep2-calculate",
                                        b.calculate_text_embedding, skip_exist,
                                        st_show_detail_number=True, st_show_detail_project_id=True, st_button_icon="✨", )


def _step3_testing():
    pass


main()
