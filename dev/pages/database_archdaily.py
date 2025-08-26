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
    tab1, tab2, tab3 = st.tabs(["Step1-上传content", "Step2-计算文本嵌入向量", "Step3-计算图像嵌入向量"])
    with tab1:
        _step1_upload_content()
    with tab2:
        _step2_calculate_text_embedding()
    with tab3:
        _step3_calculate_image_embedding()


def _step1_upload_content():
    skip_exist = st.checkbox("跳过已存在的项目", key="DBStep1-upload")
    b.template_start_work_with_progress("上传项目", "DBStep1-upload",
                                        b.archdaily__upload_content, skip_exist,
                                        st_show_detail_number=True, st_show_detail_project_id=True,
                                        st_button_icon="✨", )


def _step2_calculate_text_embedding():
    st.info("首先扫描需要计算嵌入向量的项目")
    col1, col2 = st.columns(2)
    with col1:
        skip_exist = st.checkbox("跳过已存在的项目", key="DBStep2-skip", value=True)
    with col2:
        delete_exist = st.checkbox("删除已存在的项目", key="DBStep2-delete", value=False)
    if not skip_exist:
        st.warning("不勾选[跳过已存在的项目]，可能会产生重复项目")
    if delete_exist:
        st.warning("勾选[删除已存在的项目]，会删除已存在的项目，请谨慎使用")
    collection_name = "content_embedding"
    st.info(f"请确认要操作的collection名称: **{collection_name}**")
    b.template_start_work_with_progress("扫描需要计算嵌入向量的项目", "DBStep2-scan",
                                        b.common__scan_embedding_db,
                                        user_settings.mongodb_archdaily_db_name,
                                        collection_name,
                                        user_settings.archdaily_projects_dir,
                                        skip_exist,
                                        delete_exist,
                                        st_show_detail_number=True, st_show_detail_project_id=True,
                                        st_button_icon="🔍", st_button_type="secondary")
    st.divider()
    # st.info("计算嵌入向量并写入数据库")
    _plan = st.radio("选择计算嵌入向量的方案", ["**方案1**", "**方案2**"], captions=["multimodal_embedding_v1(online)", "gme_Qwen2_vl_2B(local)"],
                     horizontal=True)

    def _plan1_region():
        st.caption("使用阿里云提供的在线API计算嵌入向量， 输出维度1024")
        st.warning("该方案速度较慢，目前已不推荐，请使用本地部署的方案2")
        b.template_project_id_queue_info_box("需要计算嵌入向量的项目", "DBStep2-calculate1")
        b.template_start_work_with_progress("计算嵌入向量(使用multimodal_embedding_v1)", "DBStep2-calculate1",
                                            b.common__calculate_text_embedding_using_multimodal_embedding_v1_api,
                                            user_settings.mongodb_archdaily_db_name,
                                            collection_name,
                                            st_show_detail_number=True, st_show_detail_project_id=True,
                                            st_button_icon="✨", ctx_enable_ctx_scope_check=True)

    def _plan2_region():
        st.caption("使用本地部署的gme-Qwen2-VL-2B-Instruct， 输出维度1536")
        b.template_project_id_queue_info_box("需要计算嵌入向量的项目", "DBStep2-calculate2")
        b.template_start_work_with_progress("计算嵌入向量(使用gme-Qwen2-VL-2B-Instruct)", "DBStep2-calculate2",
                                            b.common__calculate_text_embedding_using_gme_Qwen2_VL_2B_api,
                                            user_settings.mongodb_archdaily_db_name,
                                            collection_name,
                                            st_show_detail_number=True, st_show_detail_project_id=True,
                                            st_button_icon="✨", ctx_enable_ctx_scope_check=True)

    # 添加Qwen2.5-VL-32B-Instruct新方案
    def _plan3_region():
        st.caption("使用本地部署的Qwen2.5-VL-32B-Instruct， 输出维度4096")
        b.template_project_id_queue_info_box("需要计算嵌入向量的项目", "DBStep2-calculate3")
        b.template_start_work_with_progress("计算嵌入向量(使用Qwen2.5-VL-32B-Instruct)", "DBStep2-calculate3",
                                            b.common__calculate_text_embedding_using_qwen2_5_VL_32B_Instruct,
                                            user_settings.mongodb_archdaily_db_name,
                                            collection_name,
                                            st_show_detail_number=True, st_show_detail_project_id=True,
                                            st_button_icon="✨", ctx_enable_ctx_scope_check=True)

    if _plan == "**方案1**":
        _plan1_region()
    elif _plan == "**方案2**":
        _plan2_region()
    elif _plan == "**方案3**":
        _plan3_region()



def _step3_calculate_image_embedding():
    st.info("首先扫描需要计算嵌入向量的项目")

    image_processor_type = st.selectbox("选择Image Processor名称", ["default", "canny"])
    image_processors = b.get_image_processors(image_processor_type)
    image_processor_name_to_image_processor = {image_processor.name: image_processor for image_processor in image_processors}
    image_processor_name = st.selectbox("选择Image Processor", list(image_processor_name_to_image_processor.keys()))
    if image_processor_name not in image_processor_name_to_image_processor.keys():
        st.error(f"Image Processor {image_processor_name} not found")
        return
    input_image_dir = st.text_input("输入图片文件夹路径", value="image_gallery/large")
    if not input_image_dir:
        st.error("请输入图片文件夹路径")
        return
    col1, col2 = st.columns(2)
    with col1:
        skip_exist = st.checkbox("跳过已存在的项目", key="DBStep3-skip", value=True)
    with col2:
        delete_exist = st.checkbox("删除已存在的项目", key="DBStep3-delete", value=False)
    if not skip_exist:
        st.warning("不勾选[跳过已存在的项目]，可能会产生重复项目")
    if delete_exist:
        st.warning("勾选[删除已存在的项目]，会删除已存在的项目，请谨慎使用")
    collection_name = f"image_embedding_{image_processor_name}"
    st.info(f"请确认要操作的collection名称: **{collection_name}**")
    b.template_start_work_with_progress("扫描需要计算嵌入向量的项目", "DBStep3-scan",
                                        b.common__scan_embedding_db,
                                        user_settings.mongodb_archdaily_db_name,
                                        collection_name,
                                        user_settings.archdaily_projects_dir,
                                        skip_exist,
                                        delete_exist,
                                        st_show_detail_number=True, st_show_detail_project_id=True,
                                        st_button_icon="🔍", st_button_type="secondary")
    st.divider()

    st.caption("使用本地部署的gme-Qwen2-VL-2B-Instruct进行图片向量嵌入， 输出维度1536")

    b.template_project_id_queue_info_box("需要计算嵌入向量的项目", "DBStep3-calculate2")
    b.template_start_work_with_progress("计算嵌入向量(使用gme-Qwen2-VL-2B-Instruct)", "DBStep3-calculate2",
                                        b.common__calculate_image_embedding_using_gme_Qwen2_VL_2B_api,
                                        user_settings.mongodb_archdaily_db_name,
                                        collection_name,
                                        user_settings.archdaily_projects_dir,
                                        input_image_dir,
                                        image_processor_type,
                                        image_processor_name,
                                        st_show_detail_number=True, st_show_detail_project_id=True,
                                        st_button_icon="✨", ctx_enable_ctx_scope_check=True)

# 在 _step3_calculate_image_embedding 函数中添加新方案
def _plan3_region():
    st.caption("使用本地部署的Qwen2.5-VL-32B-Instruct进行图片向量嵌入， 输出维度4096")
    b.template_project_id_queue_info_box("需要计算嵌入向量的项目", "DBStep3-calculate3")
    b.template_start_work_with_progress("计算嵌入向量(使用Qwen2.5-VL-32B-Instruct)", "DBStep3-calculate3",
                                        b.common__calculate_image_embedding_using_qwen2_5_VL_32B_Instruct,
                                        user_settings.mongodb_archdaily_db_name,
                                        collection_name,
                                        user_settings.archdaily_projects_dir,
                                        input_image_dir,
                                        image_processor_type,
                                        image_processor_name,
                                        st_show_detail_number=True, st_show_detail_project_id=True,
                                        st_button_icon="✨", ctx_enable_ctx_scope_check=True)



main()
