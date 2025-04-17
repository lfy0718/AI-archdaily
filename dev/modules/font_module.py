import logging

import imgui
import os
from dev.global_app_state import g
from config import *
from dev.modules import BaseModule
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FontModule(BaseModule):
    @classmethod
    def m_init(cls):
        """
        font 模块比较特殊，font的创建应该使用下方的m_create_fonts方法，在创建modern gl window renderer之前完成
        """
        super().m_init()
        # from src.modules import EventModule
        # EventModule.register_global_scale_change_callback(cls._on_global_scale_changed)
        # EventModule.register_language_change_callback(cls._on_language_changed)

    @classmethod
    def m_create_fonts(cls):
        """this should be run before ModernglWindowRenderer(self.wnd)"""

        logging.info(f"[{cls.__name__}] Creating fonts...")
        io = imgui.get_io()
        fonts: imgui.core._FontAtlas = io.fonts

        # if user_settings.language == 0:  # English
        #     glyph_ranges = fonts.get_glyph_ranges_default()
        # elif user_settings.language == 1:
        #     glyph_ranges = fonts.get_glyph_ranges_chinese_full()
        # else:
        #     raise Exception(f"unsupported language ({user_settings.language})")

        glyph_ranges = fonts.get_glyph_ranges_chinese_full()

        msyh = fonts.add_font_from_file_ttf(
            os.path.join(RESOURCES_DIR, 'fonts/msyh.ttf'), g.font_size,
            glyph_ranges=glyph_ranges)
        msyh_bd = fonts.add_font_from_file_ttf(
            os.path.join(RESOURCES_DIR, 'fonts/msyhbd.ttf'), g.font_size,
            glyph_ranges=glyph_ranges)
        msyh_l = fonts.add_font_from_file_ttf(
            os.path.join(RESOURCES_DIR, 'fonts/msyh.ttf'), g.font_size * 1.5,
            glyph_ranges=fonts.get_glyph_ranges_default())
        msyh_xl = fonts.add_font_from_file_ttf(
            os.path.join(RESOURCES_DIR, 'fonts/msyh.ttf'), g.font_size * 2,
            glyph_ranges=fonts.get_glyph_ranges_default())
        msyh_xxl = fonts.add_font_from_file_ttf(
            os.path.join(RESOURCES_DIR, 'fonts/msyh.ttf'), g.font_size * 4,
            glyph_ranges=fonts.get_glyph_ranges_default())

        # node_editor_font = fonts.add_font_from_file_ttf(
        #     os.path.join(RESOURCES_DIR, 'fonts/msyh.ttf'), 16,
        #     glyph_ranges=fonts.get_glyph_ranges_chinese())

        g.mFont = msyh
        g.mFontBold = msyh_bd
        g.mFontL = msyh_l
        g.mFontXL = msyh_xl
        g.mFontXXL = msyh_xxl
        g.mNodeEditorFont = msyh
        g.mNodeEditorFontBold = msyh

    #
    # @classmethod
    # def m_update_fonts(cls):
    #     logging.info(f"[{cls.__name__}] Updating fonts")
    #     cls.m_create_fonts()
    #     g.mWindowEvent.imgui.refresh_font_texture()
    #
    # @classmethod
    # def _on_global_scale_changed(cls):
    #     cls.m_update_fonts()
    #
    # @classmethod
    # def _on_language_changed(cls):
    #     cls.m_update_fonts()
