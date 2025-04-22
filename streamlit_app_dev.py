# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/21/2025 3:37 PM
# @Function:
import os.path

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import logging
logging.basicConfig(level=logging.INFO,
                    format="%(levelname)-8s %(asctime)-24s %(filename)-24s:%(lineno)-4d | %(message)s")
logging.getLogger("PIL").setLevel(logging.WARNING)  # Disable PIL's DEBUG output
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load config
with open('./.streamlit/auth.yaml') as file:
    auth_config = yaml.load(file, Loader=SafeLoader)

# Initialize Authenticator
authenticator = stauth.Authenticate(
    auth_config['credentials'],
    auth_config['cookie']['name'],
    auth_config['cookie']['key'],
    auth_config['cookie']['expiry_days']
)

# Authenticate
if not st.session_state.get('authentication_status'):
    token = authenticator.cookie_controller.get_cookie()
    if token:
        # Try to log in with the token
        authenticator.authentication_controller.login(token=token)

pages_folder = "./dev/pages"
if st.session_state.get('authentication_status'):
    # Show Main content
    pages = {
        "🏠Home": [st.Page(os.path.join(pages_folder, "main_page.py"), title="HomePage"), ],
        "🌍Scraping": [
            st.Page(os.path.join(pages_folder, "scraping_archdaily.py"), title="Scraping Archdaily"),
            st.Page(os.path.join(pages_folder, "scraping_gooood.py"), title="Scraping Gooood"),
        ],
        "🌿Database": [
            st.Page(os.path.join(pages_folder, "database_archdaily.py"), title="Manage Archdaily Database"),
            st.Page(os.path.join(pages_folder, "database_gooood.py"), title="Manage Gooood Database"),
        ],
        "Chat": [
            st.Page(os.path.join(pages_folder, "chat_archdaily.py"), title="Chat Archdaily"),

        ]
    }

    pg = st.navigation(pages)
    pg.run()

else:
    # Show Log in page
    pages = {
        "Blank": [st.Page(os.path.join(pages_folder, "blank.py"), title="Blank"), ],
    }
    pg = st.navigation(pages)
    pg.run()


# 下方代码在每个页面结束后都会运行
def _logout(*args, **kwargs):
    authenticator.authentication_controller.logout()
    authenticator.cookie_controller.delete_cookie()
    st.session_state['authentication_status'] = None
    st.rerun(scope="app")


try:
    authenticator.login(single_session=True)
except Exception as e:
    st.error(e)

if st.session_state.get('authentication_status'):
    authenticator.logout(callback=_logout, location='sidebar', use_container_width=True)
elif st.session_state.get('authentication_status') is False:
    st.error('Username/password is incorrect')
elif st.session_state.get('authentication_status') is None:
    st.warning('Please enter your username and password')
