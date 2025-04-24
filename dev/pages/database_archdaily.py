# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/21/2025 4:35 PM
# @Function:

import streamlit as st
from dev import backend as b

config = b.load_config()
user_settings = config.user_settings


def main():
    st.markdown("# Archdaily 数据库管理")
    b.template_mongodb_connection_region(user_settings.mongodb_archdaily_db_name,
                                         lambda db_name: setattr(user_settings, 'mongodb_archdaily_db_name', db_name))
    tab1, tab2, tab3 = st.tabs(["Step1-上传content", "Step2-计算嵌入向量", "Step3-测试"])
    with tab1:
        _step1_upload_content()
    with tab2:
        _step2_calculating_embedding()
    with tab3:
        _step3_testing()


def _step1_upload_content():
    skip_exist = st.checkbox("跳过已存在的项目", key="DBStep1-upload")
    b.template_start_work_with_progress("上传项目", "DBStep1-upload",
                                        b.archdaily__upload_content, skip_exist,
                                        st_show_detail_number=True, st_show_detail_project_id=True,
                                        st_button_icon="✨", )


def _step2_calculating_embedding():
    st.info("首先扫描需要计算嵌入向量的项目")
    skip_exist = st.checkbox("跳过已存在的项目", key="DBStep2-calculate", value=True)
    if not skip_exist:
        st.warning("不勾选该选项，会清除已经存在embedding的项目数据，请谨慎选择")
    b.template_start_work_with_progress("扫描需要计算嵌入向量的项目", "DBStep2-scan",
                                        b.archdaily__scan_embedding_db, skip_exist,
                                        st_show_detail_number=True, st_show_detail_project_id=True,
                                        st_button_icon="🔍", st_button_type="secondary")
    st.divider()
    # st.info("计算嵌入向量并写入数据库")
    _plan = st.radio("选择计算嵌入向量的方案", ["**方案1**", "**方案2**"], captions=["multimodal_embedding_v1(online)", "gme_Qwen2_vl_2B(local)"],
                     horizontal=True)

    def _plan1_region():
        st.caption("使用阿里云提供的在线API计算嵌入向量， 输出维度1024")
        st.warning("该方案速度较慢，目前已不推荐，请使用本地部署的方案2")
        b.template_project_id_queue_info_box("需要计算嵌入向量的项目", "DBStep2-calculate2")
        b.template_start_work_with_progress("计算嵌入向量(使用multimodal_embedding_v1)", "DBStep2-calculate1",
                                            b.archdaily__calculate_text_embedding_using_multimodal_embedding_v1_api,
                                            st_show_detail_number=True, st_show_detail_project_id=True,
                                            st_button_icon="✨", ctx_enable_ctx_scope_check=True)

    def _plan2_region():
        st.caption("使用本地部署的gme-Qwen2-VL-2B-Instruct， 输出维度1536")
        b.template_project_id_queue_info_box("需要计算嵌入向量的项目", "DBStep2-calculate2")
        b.template_start_work_with_progress("计算嵌入向量(使用gme-Qwen2-VL-2B-Instruct)", "DBStep2-calculate2",
                                            b.archdaily__calculate_text_embedding_using_gme_Qwen2_VL_2B_api,
                                            st_show_detail_number=True, st_show_detail_project_id=True,
                                            st_button_icon="✨", ctx_enable_ctx_scope_check=True)
        st.divider()
        b.template_start_work_with_progress("修复嵌入向量中的nan", "DBStep2-fix",
                                            b.common__fix_nan_embeddings_using_gme_Qwen2_VL_2B_api, user_settings.mongodb_archdaily_db_name,
                                            st_show_detail_number=True, st_show_detail_project_id=True,
                                            ctx_enable_ctx_scope_check=False)
    if _plan == "**方案1**":
        _plan1_region()
    elif _plan == "**方案2**":
        _plan2_region()



def _step3_testing():
    pass


main()
