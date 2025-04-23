import logging
import streamlit as st
from dev import backend as b


def main():
    st.markdown("# Scraping Gooood")

    tab1, tab2, tab3, tab4 = st.tabs(["Step1-爬取pages", "Step2-初始化项目文件夹", "Step3-解析项目内容", "Step4-下载图像"])
    with tab1:
        _step1()
    with tab2:
        _step2()
    with tab3:
        _step3()
    with tab4:
        _step4()

    st.divider()
    st.caption("数据来源: www.gooood.cn")


def _step1():
    st.subheader("步骤1： 爬取pages")
    get_all = st.checkbox("爬取所有页面", value=True)

    if not get_all:
        col1, col2 = st.columns(2)
        start_page = col1.number_input("起始页码",value=1, min_value=1)
        end_page = col2.number_input("结束页码", value=100, min_value=1)
    else:
        start_page = 1
        end_page = 1
    skip_exist = st.checkbox("跳过已经存在的page")
    if skip_exist:
        st.info("页面内容可能随日期而不同，请注意")

    b.template_start_work_with_progress("下载项目html页面到本地", "GDStep1-page",
                                        b.gooood__scrap_pages, get_all, start_page, end_page, skip_exist,
                                        st_show_detail_number=True, st_show_detail_project_id=True,
                                        ctx_enable_ctx_scope_check=False)



def _step2():
    st.subheader("步骤2： 初始化项目文件夹")
    skip_exist = st.checkbox("跳过已经存在的<project_id>.json", True)
    b.template_start_work_with_progress("开始初始化", "GDStep2-init",
                                        b.gooood__init_projects, skip_exist,
                                        st_show_detail_number=False, st_show_detail_project_id=False,
                                        ctx_enable_ctx_scope_check=False)
def _step3():
    st.subheader("步骤3： 解析项目内容，生成content.json")
    skip_exist = st.checkbox("跳过已经存在的content.json", True)
    b.template_flags("gooood")
    b.template_start_work_with_progress("开始解析项目", "GDStep3-content",
                                        b.gooood__parse_projects, b.g.flag_states['gooood'], skip_exist,
                                        st_show_detail_number=True, st_show_detail_project_id=True, st_button_icon="✨",
                                        ctx_enable_ctx_scope_check=False)


def _step4():
    st.subheader("步骤4： 下载图像")
    st.info(" 首先需要扫描本地文件")
    result = b.template_start_work_with_progress("开始扫描", "GDStep4-scan",
                                                 b.gooood__scan_projects_folder_for_downloading_images,
                                                 st_button_type='secondary', st_button_icon="🔍")
    if 'final_msg' in result:
        st.info(result['final_msg'])

    st.divider()

    b.template_project_id_queue_info_box("需要下载图片的项目", "GDStep4-download")
    b.template_start_work_with_progress("开始下载Image Gallery", "GDStep4-download",
                                        b.gooood__download_gallery_images,
                                        st_show_detail_number=True, st_show_detail_project_id=True, st_button_icon="✨",
                                        ctx_enable_ctx_scope_check=True)


main()
