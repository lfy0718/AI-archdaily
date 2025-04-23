# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/21/2025 3:39 PM
# @Function:
import logging
import streamlit as st
from dev import backend as b


def main():
    st.markdown("# Scraping Archdaily")

    tab1, tab2, tab3 = st.tabs(["Step1-下载html", "Step2-解析html", "Step3-下载图片"])
    with tab1:
        _step1_download_html()
    with tab2:
        _step2_parse_html()
    with tab3:
        _step3_download_images()

    st.divider()
    st.caption("数据来源: www.archdaily.com")


def _step1_download_html():
    st.subheader("步骤1： 下载项目html页面到本地")

    st.info(" 首先需要扫描本地文件，确定需要爬取的范围")
    _plan = st.radio("选择扫描方案", ["**方案1**", "**方案2**"], captions=["从现有文件夹扫描", "手动指定项目id范围"], horizontal=True)

    def _plan1_region():
        st.caption("此方案将扫描现有项目文件夹中是否存在content.html， 如果没有则补充")
        b.template_start_work_with_progress("扫描需要下载的项目id", "Step1-scan1",
                                            b.scan_projects_folder,
                                            st_button_type='secondary', st_button_icon="🔍")

    def _plan2_region():
        st.caption("此方案将下载指定范围内的html页面到本地（排除已经记录的404页面和已经存在的页面）")
        col1, col2 = st.columns(2)
        with col1:
            start_id = st.number_input("开始id", value=100000, step=1)
        with col2:
            end_id = st.number_input("结束id", value=100100, step=1)
        st.caption(f"已选择的项目数量: {abs(start_id - end_id)}")
        b.template_start_work_with_progress("扫描需要下载的项目id", "Step1-scan2",
                                            b.scan_valid_project_id, start_id, end_id,
                                            st_button_type='secondary', st_button_icon="🔍")


    if _plan == "**方案1**":
        _plan1_region()
    elif _plan == "**方案2**":
        _plan2_region()

    st.divider()

    b.template_project_id_queue_info_box("需要下载的html项目", "Step1-html")
    b.template_start_work_with_progress("下载项目html页面到本地", "Step1-html",
                                        b.download_projects_html_to_local,
                                        st_show_detail_number=True, st_show_detail_project_id=True, st_button_icon="📂",
                                        ctx_enable_ctx_scope_check=True)


def _step2_parse_html():
    st.subheader("步骤2： 解析项目html文件")
    st.info(" 首先需要扫描本地文件")
    skip_exist = st.checkbox("跳过已经存在的content.json")
    result = b.template_start_work_with_progress("开始扫描", "Step2-scan",
                                                 b.scan_projects_folder_for_parsing_content, skip_exist,
                                                 st_button_type='secondary', st_button_icon="🔍")
    if "num_projects_with_no_content_html" in result and result['num_projects_with_no_content_html']:
        st.warning(f"{result['num_projects_with_no_content_html']}个项目没有content.html，请注意")
    if 'final_msg' in result:
        st.info(result['final_msg'])
    st.divider()

    def on_change(_flag_name: str):
        ss_key_value = st.session_state[f'key_{_flag_name}']
        st.session_state[_flag_name] = ss_key_value
        b.g.flag_states[_flag_name] = ss_key_value
        logging.info(f"{_flag_name} set to {ss_key_value}")

    def make_on_change(_flag_name: str):
        # 创建闭包函数
        return lambda: on_change(_flag_name)

    for flag_name in b.g.flag_states:
        if flag_name not in st.session_state:
            st.session_state[flag_name] = b.g.flag_states[flag_name]
        st.checkbox(flag_name, value=st.session_state[flag_name], key=f"key_{flag_name}", on_change=make_on_change(flag_name))

    b.template_project_id_queue_info_box("需要解析的html", "Step2-html")
    b.template_start_work_with_progress("开始解析html", "Step2-html",
                                        b.parse_htmls, b.g.flag_states,
                                        st_show_detail_number=True, st_show_detail_project_id=True, st_button_icon="✨",
                                        ctx_enable_ctx_scope_check=True)


def _step3_download_images():
    st.subheader("步骤3： 下载图像")
    st.info(" 首先需要扫描本地文件")
    result = b.template_start_work_with_progress("开始扫描", "Step3-scan",
                                                 b.scan_projects_folder_for_downloading_images,
                                                 st_button_type='secondary', st_button_icon="🔍")
    if 'final_msg' in result:
        st.info(result['final_msg'])

    st.divider()

    b.template_project_id_queue_info_box("需要下载图片的项目", "Step3-download")
    b.template_start_work_with_progress("开始下载Image Gallery", "Step3-download",
                                        b.download_gallery_images,
                                        st_show_detail_number=True, st_show_detail_project_id=True,
                                        ctx_enable_ctx_scope_check=True)


main()
