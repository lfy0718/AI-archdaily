# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/21/2025 3:37 PM
# @Function:
import logging
import os.path

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from dev import backend as b
from config import user_settings

logging.basicConfig(level=logging.INFO,
                    format="%(levelname)-8s %(asctime)-24s %(filename)-24s:%(lineno)-4d | %(message)s")
logging.getLogger("PIL").setLevel(logging.WARNING)  # Disable PIL's DEBUG output
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============ Canny Page ============
def page_canny():
    st.title("Canny 线稿批处理")
    st.caption("不改动每个项目的 image_gallery/large，仅将线稿保存到 image_gallery/canny")

    st.subheader("步骤一：批量生成 Canny 线稿")
    b.template_start_work_with_progress(
        "开始批量生成 Canny 线稿",
        "archdaily-canny-batch",
        b.common__generate_canny_for_real_photos,
        user_settings.archdaily_projects_dir, 512, 5, 1.2, 0.4, 1.3,
        st_button_icon="🖼️",
    )

    st.divider()

    st.subheader("步骤二：将 Canny 结果入库 MongoDB")
    st.caption("扫描各项目 image_gallery/canny，将图片信息写入 MongoDB 集合")
    col1, col2 = st.columns(2)
    with col1:
        skip_exist_canny_upload = st.checkbox("跳过已存在的Canny图片", value=True, key="canny_upload_skip_exist_page")
    with col2:
        overwrite_canny_upload = st.checkbox("覆盖已存在的Canny图片", value=False, key="canny_upload_overwrite_page")

    b.template_start_work_with_progress(
        "入库 Canny 结果到 MongoDB",
        "archdaily-canny-upload-db",
        b.common__upload_canny_images,
        user_settings.mongodb_archdaily_db_name,
        user_settings.archdaily_projects_dir,
        'canny_images',
        skip_exist_canny_upload,
        overwrite_canny_upload,
        st_button_icon="💾",
    )


@st.cache_resource
def load_auth_config():
    """从本地加载登录信息，使用 `@st.cache_resource` 使其在整个程序生命周期仅加载一次"""
    with open('./.streamlit/auth.yaml') as file:
        _auth_config = yaml.load(file, Loader=SafeLoader)
    return _auth_config


auth_config = load_auth_config()
authenticator = stauth.Authenticate(
    auth_config['credentials'],
    auth_config['cookie']['name'],
    auth_config['cookie']['key'],
    auth_config['cookie']['expiry_days']
)

# Authenticate
# 当session state中没有authentication_status时，可能是页面刷新，首先从cookie中寻找登录信息
if not st.session_state.get('authentication_status'):
    if token := authenticator.cookie_controller.get_cookie():  # := 符号为turtle命名法
        authenticator.authentication_controller.login(token=token)  # Try to log in with the token

PAGES_FOLDER = "./dev/pages"

# authentication_status有三种状态，True, False, None
if st.session_state.get('authentication_status'):
    # 如果能够获取登录信息，并且为True，则显示导航栏
    # 注意这里设置页面信息后，每个具体的页面就不要使用st.config来配置页面信息了
    pages = {
        "🏠Home": [st.Page(os.path.join(PAGES_FOLDER, "main_page.py"), title="HomePage"), ],
        "🌍Scraping": [
            st.Page(os.path.join(PAGES_FOLDER, "scraping_archdaily.py"), title="Scraping Archdaily"),
            st.Page(os.path.join(PAGES_FOLDER, "scraping_gooood.py"), title="Scraping Gooood"),
        ],
        "🌿Database": [
            st.Page(os.path.join(PAGES_FOLDER, "database_archdaily.py"), title="Manage Archdaily Database"),
            st.Page(os.path.join(PAGES_FOLDER, "database_gooood.py"), title="Manage Gooood Database"),
        ],
        "🖼️Canny": [
            st.Page(page_canny, title="Canny 线稿批处理"),
        ],
        "Chat": [
            st.Page(os.path.join(PAGES_FOLDER, "chat_archdaily.py"), title="Chat Archdaily"),
        ]
    }
    # 配置目录的代码必须在任何st代码运行前运行
    pg = st.navigation(pages)
    pg.run()

else:
    # 如果没有登录，则显示空白页面
    # Show Log in page
    pages = {
        "Blank": [st.Page(os.path.join(PAGES_FOLDER, "blank.py"), title="Blank"), ],
    }
    pg = st.navigation(pages)
    pg.run()


# [===每个页面的代码实际会运行在这个位置===]

# 下方代码在每个页面结束后都会运行，但是只有在没有登录时才有具体内容
def _logout(*args, **kwargs):
    """手动进行logout，代码复制并修改自authenticator.logout方法"""
    authenticator.authentication_controller.logout()
    authenticator.cookie_controller.delete_cookie()
    st.session_state['authentication_status'] = None
    st.rerun(scope="app")


try:
    authenticator.login(single_session=True)  # 显示登录页面（仅在没有登录时有内容）
except Exception as e:
    st.error(e)

if st.session_state.get('authentication_status'):
    # 如果登录，在侧边栏显示登出按钮
    authenticator.logout(callback=_logout, location='sidebar', use_container_width=True)
elif st.session_state.get('authentication_status') is False:
    # 如果登录失败，显示错误信息
    st.error('Username/password is incorrect')
elif st.session_state.get('authentication_status') is None:
    # 如果登录状态为None，显示提示信息
    st.warning('Please enter your username and password')
