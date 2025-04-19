import logging
import os
import time
import uuid
from collections import deque
from typing import Callable, Union, Iterable, Optional, Literal

import imgui
import pyperclip

from dev.global_app_state import g
from dev.utils import io_utils, color_utils

__runtime__ = True
if not __runtime__:
    from dev.modules.graphic_module import SimpleTexture
    from imgui.core._ImGuiInputTextCallbackData import _ImGuiInputTextCallbackData
    from dev.modules import DrawingModule, TextureModule, StyleModule, GraphicModule


class Components:
    _Instance = None

    _ImguiStyle: Optional[imgui.core.GuiStyle] = None
    _DrawingModule: Optional["type(DrawingModule)"] = None
    _StyleModule: Optional["type(StyleModule)"] = None
    _TextureModule: Optional["type(TextureModule)"] = None
    _GraphicModule: Optional["type(GraphicModule)"] = None
    _SimpleTexture: Optional["type(SimpleTexture)"] = None

    DEFAULT_TABLE_FLAGS = imgui.TABLE_RESIZABLE | imgui.TABLE_REORDERABLE | imgui.TABLE_ROW_BACKGROUND | imgui.TABLE_BORDERS_VERTICAL | imgui.TABLE_SIZING_FIXED_FIT

    def __init__(self):
        assert Components._Instance is None, " Only one component instance can be created"
        Components._Instance = self

    @staticmethod
    def c_init():
        from dev.global_app_state import g
        Components._ImguiStyle = g.mImguiStyle
        from dev.modules import DrawingModule, TextureModule, StyleModule, GraphicModule
        Components._DrawingModule = DrawingModule
        Components._TextureModule = TextureModule
        Components._StyleModule = StyleModule
        Components._GraphicModule = GraphicModule
        from dev.modules.graphic_module import SimpleTexture
        Components._SimpleTexture = SimpleTexture

    @staticmethod
    def c_update():
        Components._TextureModule.GalleryTextureInfo.update_gallery_texture_info()

    @staticmethod
    def c_render():
        pass

    @staticmethod
    def c_late_update():
        """put your late update functions here, This code is executed in the Late Update section of UIManager"""
        pass

    @staticmethod
    def icon_button(icon_name, width=None, height=None, tint_color=(1, 1, 1, 1),
                    border_color=(0, 0, 0, 0), bg_color=(0, 0, 0, 0), tooltip=None, id=None) -> bool:
        tint_color = color_utils.align_alpha(tint_color, g.mImguiStyle.colors[imgui.COLOR_BUTTON])
        rounding = g.mImguiStyle.frame_rounding
        icon_height = imgui.get_frame_height() if height is None else height
        icon_width = icon_height if width is None else width
        icon_height -= rounding * 2
        icon_width -= rounding * 2
        imgui.push_style_color(imgui.COLOR_BUTTON, *bg_color)
        imgui.push_style_var(imgui.STYLE_FRAME_PADDING, (rounding, rounding))
        if id is not None:
            imgui.push_id(str(id))
        glo, uv0, uv1 = Components._TextureModule.get_icon_glo(icon_name)
        clicked = imgui.image_button(glo, icon_width, icon_height, uv0, uv1, tint_color,
                                     border_color, -1)
        if id is not None:
            imgui.pop_id()
        imgui.pop_style_color(1)
        imgui.pop_style_var(1)
        Components.easy_tooltip(tooltip)

        return clicked

    @staticmethod
    def image_button(texture_name, width=None, height=None, uv0=(0, 0), uv1=(1, 1), tint_color=(1, 1, 1, 1),
                     border_color=(0, 0, 0, 0), bg_color=(0, 0, 0, 0), tooltip=None, id=None) -> bool:
        glo = Components._TextureModule.get_texture_glo(texture_name)
        return Components.image_button_using_glo(glo, width, height, uv0, uv1, tint_color, border_color, bg_color,
                                                 tooltip, id)

    @staticmethod
    def image_button_using_glo(texture_glo, width=None, height=None, uv0=(0, 0), uv1=(1, 1), tint_color=(1, 1, 1, 1),
                               border_color=(0, 0, 0, 0), bg_color=(0, 0, 0, 0), tooltip=None, id=None) -> bool:
        tint_color = color_utils.align_alpha(tint_color, g.mImguiStyle.colors[imgui.COLOR_BUTTON])
        rounding = g.mImguiStyle.frame_rounding
        icon_height = imgui.get_frame_height() if height is None else height
        icon_width = icon_height if width is None else width
        icon_height -= rounding * 2
        icon_width -= rounding * 2
        imgui.push_style_color(imgui.COLOR_BUTTON, *bg_color)
        imgui.push_style_var(imgui.STYLE_FRAME_PADDING, (rounding, rounding))
        if id is not None:
            imgui.push_id(str(id))
        clicked = imgui.image_button(texture_glo, icon_width, icon_height, uv0, uv1, tint_color,
                                     border_color, -1)
        if id is not None:
            imgui.pop_id()
        imgui.pop_style_color(1)
        imgui.pop_style_var(1)
        Components.easy_tooltip(tooltip)

        return clicked

    @staticmethod
    def _move_cursor_to_h_center_by_precalculated_text_size(text_size: tuple[float]):
        text_width = text_size[0]
        width = imgui.get_content_region_available()[0]
        x = imgui.get_cursor_pos_x()
        indent = (width - text_width) / 2
        imgui.set_cursor_pos_x(x + indent)

    @staticmethod
    def _move_cursor_to_v_center_by_precalculated_text_size(text_size: tuple[float]):
        text_height = text_size[1]
        height = imgui.get_frame_height()
        y = imgui.get_cursor_pos_y()
        indent = (height - text_height) / 2
        imgui.set_cursor_pos_y(y + indent)

    @staticmethod
    def _move_cursor_to_center_by_text_size(content: str):
        Components._move_cursor_to_h_center_by_precalculated_text_size(imgui.calc_text_size(content))

    @staticmethod
    def _move_cursor_to_v_center_by_text_size(content: str):
        Components._move_cursor_to_v_center_by_precalculated_text_size(imgui.calc_text_size(content))

    @staticmethod
    def _move_cursor_to_center_by_button_width(button_width):
        width = imgui.get_content_region_available()[0]
        x = imgui.get_cursor_pos_x()
        indent = (width - button_width) / 2
        imgui.set_cursor_pos_x(x + indent)

    @staticmethod
    def ctext(content, h_center=False, v_center=False):
        if h_center or v_center:
            size = imgui.calc_text_size(content)
            if h_center:
                Components._move_cursor_to_h_center_by_precalculated_text_size(size)
            if v_center:
                Components._move_cursor_to_v_center_by_precalculated_text_size(size)
        imgui.text(content)

    @staticmethod
    def bold_text(content, h_center=False, v_center=False):
        with imgui.font(g.mFontBold):
            if h_center or v_center:
                size = imgui.calc_text_size(content)
                if h_center:
                    Components._move_cursor_to_h_center_by_precalculated_text_size(size)
                if v_center:
                    Components._move_cursor_to_v_center_by_precalculated_text_size(size)
            imgui.text(content)

    @staticmethod
    def gray_text(content, h_center=False, v_center=False):
        imgui.set_window_font_scale(0.8)
        if h_center or v_center:
            size = imgui.calc_text_size(content)
            if h_center:
                Components._move_cursor_to_h_center_by_precalculated_text_size(size)
            if v_center:
                Components._move_cursor_to_v_center_by_precalculated_text_size(size)
        gray_color = color_utils.align_alpha(Components._StyleModule.COLOR_GRAY, g.mImguiStyle.colors[imgui.COLOR_TEXT])
        imgui.push_style_color(imgui.COLOR_TEXT, *gray_color)
        imgui.text(content)
        imgui.pop_style_color()
        imgui.set_window_font_scale(1.0)

    @staticmethod
    def gray_text_wrapped(content):
        imgui.set_window_font_scale(0.8)
        gray_color = color_utils.align_alpha(Components._StyleModule.COLOR_GRAY, g.mImguiStyle.colors[imgui.COLOR_TEXT])
        imgui.push_style_color(imgui.COLOR_TEXT, *gray_color)
        imgui.text_wrapped(content)
        imgui.pop_style_color()
        imgui.set_window_font_scale(1.0)

    @staticmethod
    def warning_text(content, h_center=False, v_center=False):
        if h_center or v_center:
            size = imgui.calc_text_size(content)
            if h_center:
                Components._move_cursor_to_h_center_by_precalculated_text_size(size)
            if v_center:
                Components._move_cursor_to_v_center_by_precalculated_text_size(size)
        color = color_utils.align_alpha(Components._StyleModule.COLOR_WARNING, g.mImguiStyle.colors[imgui.COLOR_TEXT])
        imgui.push_style_color(imgui.COLOR_TEXT, *color)
        imgui.text(content)
        imgui.pop_style_color()

    @staticmethod
    def error_text(content, h_center=False, v_center=False):
        if h_center or v_center:
            size = imgui.calc_text_size(content)
            if h_center:
                Components._move_cursor_to_h_center_by_precalculated_text_size(size)
            if v_center:
                Components._move_cursor_to_v_center_by_precalculated_text_size(size)
        color = color_utils.align_alpha(Components._StyleModule.COLOR_DANGER, g.mImguiStyle.colors[imgui.COLOR_TEXT])
        imgui.push_style_color(imgui.COLOR_TEXT, *color)
        imgui.text(content)
        imgui.pop_style_color()

    @staticmethod
    def danger_text(content, center=False):
        Components.error_text(content, center)

    @staticmethod
    def highlight_text(content, h_center=False, v_center=False):
        if h_center or v_center:
            size = imgui.calc_text_size(content)
            if h_center:
                Components._move_cursor_to_h_center_by_precalculated_text_size(size)
            if v_center:
                Components._move_cursor_to_v_center_by_precalculated_text_size(size)
        color = color_utils.align_alpha(Components._StyleModule.COLOR_PRIMARY, g.mImguiStyle.colors[imgui.COLOR_TEXT])
        imgui.push_style_color(imgui.COLOR_TEXT, *color)
        imgui.text(content)
        imgui.pop_style_color()

    @staticmethod
    def icon_image(icon_name, width=None, height=None, uv0=(0, 0), uv1=(1, 1), tint_color=(1, 1, 1, 1),
                   border_color=(0, 0, 0, 0), padding=False):
        tint_color = color_utils.align_alpha(tint_color, g.mImguiStyle.colors[imgui.COLOR_TEXT])

        icon_height = imgui.get_frame_height() if height is None else height
        if padding:
            icon_height -= g.mImguiStyle.frame_padding[1] * 2
        icon_width = icon_height if width is None else width
        glo, uv0, uv1 = Components._TextureModule.get_icon_glo(icon_name)
        imgui.image(glo, icon_width, icon_height, uv0, uv1, tint_color, border_color)

    _selectable_region_hovering_data: dict[str: bool] = {}

    @staticmethod
    def selectable_region(uid, width: Union[int, float], height: Union[int, float], content: Callable, *args):
        width = int(width)
        height = int(height)
        if uid not in Components._selectable_region_hovering_data:
            Components._selectable_region_hovering_data[uid] = False
            is_hovering = False
        else:
            is_hovering = Components._selectable_region_hovering_data[uid]

        clicked = False
        if is_hovering:
            if imgui.is_mouse_released(0):
                imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, *g.mImguiStyle.colors[imgui.COLOR_BUTTON_ACTIVE])
                clicked = True
            elif imgui.is_mouse_down(0):
                imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, *g.mImguiStyle.colors[imgui.COLOR_BUTTON_ACTIVE])
            else:
                imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, *g.mImguiStyle.colors[imgui.COLOR_BUTTON_HOVERED])
        else:
            imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, *g.mImguiStyle.colors[imgui.COLOR_BUTTON])
        imgui.push_style_var(imgui.STYLE_CHILD_ROUNDING, g.mImguiStyle.frame_rounding)
        Components.begin_child(uid, width, height, border=False)
        # endregion
        if not clicked:
            Components._selectable_region_hovering_data[uid] = imgui.is_window_hovered()
        else:
            Components._selectable_region_hovering_data[uid] = False
        content(*args)
        imgui.end_child()
        imgui.pop_style_color(1)
        imgui.pop_style_var(1)
        return clicked

    _no_advanced_drawing = 0

    @staticmethod
    def push_no_advanced_drawing():
        Components._no_advanced_drawing += 1

    @staticmethod
    def pop_no_advanced_drawing():
        Components._no_advanced_drawing -= 1

    @staticmethod
    def no_advanced_drawing() -> bool:
        if Components._no_advanced_drawing:
            return True
        return False

    @staticmethod
    def _draw_icon_and_text(icon, text, text_width, align_center):
        pos = imgui.get_cursor_pos()
        imgui.set_cursor_pos((pos[0] + g.mImguiStyle.frame_padding[0], pos[1] + g.mImguiStyle.frame_padding[1]))
        size = imgui.get_frame_height() - g.mImguiStyle.frame_padding[1] * 2
        Components.icon_image(icon, size, size)
        imgui.same_line()
        if align_center:
            indent = (imgui.get_content_region_available_width() - text_width) / 2
            imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + indent)
        imgui.text(text)

    @staticmethod
    def advanced_button(text, width=None, height=None, button_align_center=False, text_align_center=False, uid=None):
        text_width = imgui.calc_text_size(text)[0]
        if width is None:
            width = text_width + g.mImguiStyle.frame_padding[0] * 2
        if height is None:
            height = imgui.get_frame_height()
        if button_align_center:
            Components._move_cursor_to_center_by_button_width(width)
        return Components.selectable_region(uid if uid is not None else f'button_{text}', width, height,
                                            Components._draw_text_inner_selectable_region, text, text_align_center)

    @staticmethod
    def button(text, width=0, height=0, disabled=False):
        if disabled:
            Components._StyleModule.push_disabled_button_color()
        clicked = imgui.button(text, width, height)
        if disabled:
            Components._StyleModule.pop_button_color()
        return clicked and not disabled

    @staticmethod
    def small_button(text, disabled=False):
        if disabled:
            Components._StyleModule.push_disabled_button_color()
        clicked = imgui.small_button(text)
        if disabled:
            Components._StyleModule.pop_button_color()
        return clicked and not disabled

    @staticmethod
    def highlighted_button(text, width=0, height=0, disabled=False):
        if disabled:
            Components._StyleModule.push_disabled_button_color()
        else:
            Components._StyleModule.push_highlighted_button_color()
        clicked = imgui.button(text, width, height)

        Components._StyleModule.pop_button_color()
        return clicked and not disabled

    @staticmethod
    def dangerous_button(text, width=0, height=0, disabled=False):
        if disabled:
            Components._StyleModule.push_disabled_button_color()
        else:
            Components._StyleModule.push_dangerous_button_color()
        clicked = imgui.button(text, width, height)
        Components._StyleModule.pop_button_color()
        return clicked and not disabled

    @staticmethod
    def _draw_text_inner_selectable_region(text, center=False):
        # align y
        if center:
            text_height = imgui.calc_text_size(text)[1]
            wnd_height = imgui.get_window_height()
            y = (wnd_height - text_height) / 2
            imgui.set_cursor_pos((g.mImguiStyle.frame_padding[0], y))

        Components.ctext(text, center)  # the center here only controls x-axis

    @staticmethod
    def icon_text_button(icon, text, width=None, height=None, align_center=False, uid=None):
        text_width = imgui.calc_text_size(text)[0]
        if width is None:
            width = text_width + imgui.get_frame_height() + \
                    g.mImguiStyle.item_spacing[0]
        if height is None:
            height = imgui.get_frame_height()

        return Components.selectable_region(uid if uid is not None else f'icon_text_button_{icon}_{text}', width,
                                            height,
                                            Components._draw_icon_and_text, icon, text,
                                            text_width, align_center)

    @staticmethod
    def _draw_icon_and_double_text(icon, text1, text2):
        pos = imgui.get_cursor_pos()
        imgui.set_cursor_pos((pos[0] + g.mImguiStyle.frame_padding[0], pos[1] + g.mImguiStyle.frame_padding[1]))
        size = imgui.get_frame_height() - g.mImguiStyle.frame_padding[1] * 1  # (-2 + 1) = 1 make icon bigger
        imgui.begin_group()
        Components.icon_image(icon, size, size)
        imgui.end_group()
        imgui.same_line()
        imgui.begin_group()
        imgui.text(text1)
        gray_color = color_utils.align_alpha(Components._StyleModule.COLOR_GRAY, g.mImguiStyle.colors[imgui.COLOR_TEXT])
        imgui.push_style_color(imgui.COLOR_TEXT, *gray_color)
        imgui.set_window_font_scale(0.8)
        imgui.text(text2)
        imgui.set_window_font_scale(1.0)
        imgui.pop_style_color()
        imgui.end_group()

    @staticmethod
    def icon_double_text_button(icon, text1, text2, width=None, height=None, uid=None):
        if width is None:
            text1_size = imgui.calc_text_size(text1)
            text2_size = imgui.calc_text_size(text2)
            max_text_width = max(text2_size[0], text1_size[0])
            width = max_text_width + imgui.get_frame_height() + g.mImguiStyle.item_spacing[0] + \
                    g.mImguiStyle.frame_padding[
                        0] * 1  # frame padding = icon(-2 + 1) + border 2 = 1
        if height is None:
            height = Components.get_icon_double_text_button_height()
        return Components.selectable_region(uid if uid is not None else f'icon_text_button_{icon}_{text1}_{text2}',
                                            width, height, Components._draw_icon_and_double_text,
                                            icon,
                                            text1, text2)

    @staticmethod
    def get_icon_double_text_button_height():
        return g.font_size * 2 + g.mImguiStyle.item_spacing[1] + g.mImguiStyle.frame_padding[1] * 2

    @staticmethod
    def easy_tooltip(content):
        if content is None or content == '':
            return
        if imgui.is_item_hovered():
            imgui.set_tooltip(content)

    @staticmethod
    def easy_question_mark(content):
        imgui.same_line()
        imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() + g.mImguiStyle.frame_padding[1])
        Components.icon_image('question-line', padding=True, tint_color=(0.5, 0.5, 0.5, 0.5))
        Components.easy_tooltip(content)

    _cached_image_gallery_preview_textures_info = {}  # path, texture
    _right_clicked_tex_info = None

    @staticmethod
    def image_gallery(name, folder_path, texture_infos: dict[str:"TextureModule.GalleryTextureInfo"], width=0.0,
                      height=0.0,
                      columns=4, bg_color=(0, 0, 0, 0.1), show_names=True,
                      right_click_menu_content: Callable[["TextureModule.GalleryTextureInfo",
                                                          dict[str: "TextureModule.GalleryTextureInfo"]], None] = None):
        if width == 0.0:
            width = imgui.get_content_region_available_width()
        if height == 0.0:
            height = width / 2.5

        Components.begin_child(f'image_gallery_{name}', width, height, border=True, bg_color=bg_color)
        if len(texture_infos) == 0:
            Components.ctext("No Image", h_center=True, v_center=True)
            Components.end_child()
            return
        _wnd_position = imgui.get_window_position()
        _wnd_size = imgui.get_window_size()
        _wnd_min_y, _wnd_max_y = _wnd_position[1], _wnd_position[1] + _wnd_size[1]
        img_tint_color = color_utils.align_alpha(Components._StyleModule.COLOR_WHITE,
                                                 g.mImguiStyle.colors[imgui.COLOR_TEXT])
        with imgui.begin_table(f'table_{name}', columns):
            imgui.table_next_column()
            width = imgui.get_content_region_available_width()
            for _, tex_info in texture_infos.items():
                tex = tex_info.texture
                ratio = tex.width / tex.height
                height = int(width / ratio)
                break
            _open_right_click_popup = False
            for texture_name, texture_info in texture_infos.items():
                texture_info: "TextureModule.GalleryTextureInfo" = texture_info
                _img_min_y = imgui.get_cursor_screen_pos()[1]
                _img_min_x = imgui.get_cursor_screen_pos()[0]
                _img_max_y = _img_min_y + height
                _img_max_x = _img_min_x + width
                if _img_min_y > _wnd_max_y or _img_max_y < _wnd_min_y:  # image is not visible
                    # Components._DrawingModule.draw_rect(_img_min_x, _img_min_y, _img_max_x, _img_max_y, col=(1, 0, 0, 0.5), draw_list_type="foreground")
                    imgui.dummy(width, height)
                else:
                    texture: "SimpleTexture" = texture_info.texture  # 在此帧请求texture
                    # ratio = texture.width / texture.height
                    # height = int(width / ratio)
                    imgui.image(texture.glo, width, height, (0, 0), (1, 1), img_tint_color)
                if imgui.is_item_clicked(imgui.MOUSE_BUTTON_LEFT):
                    file_path = texture_info.file_path
                    if file_path in Components._cached_image_gallery_preview_textures_info:
                        g.mTmpTexture = Components._cached_image_gallery_preview_textures_info[file_path]
                    else:
                        from dev.modules.texture_module import TextureModule
                        from PIL import Image
                        try:
                            img = Image.open(file_path)
                            texture = Components._TextureModule.create_texture_from_image(img,
                                                                                          f"_preview_image_{texture_name}")
                            g.mTmpTexture = texture
                            Components._cached_image_gallery_preview_textures_info[file_path] = texture
                        except Exception as e:
                            logging.warning(f"{file_path} is not a image file.{str(e)}")
                if imgui.is_item_clicked(imgui.MOUSE_BUTTON_RIGHT):
                    Components._right_clicked_tex_info = texture_info
                    _open_right_click_popup = True
                    logging.info(f"right clicked {texture_info.file_path}")
                if show_names:
                    Components.ctext(texture_name, h_center=True)
                imgui.dummy(0, 4 * g.global_scale)
                imgui.table_next_column()
        if _open_right_click_popup:
            imgui.open_popup(f"right_click_menu_{name}")
        if imgui.begin_popup(f"right_click_menu_{name}") and Components._right_clicked_tex_info is not None:
            imgui.text(Components._right_clicked_tex_info.file_name)
            if right_click_menu_content is not None:
                right_click_menu_content(Components._right_clicked_tex_info, texture_infos)
            else:
                Components.gray_text("Right menu not registered.")
            imgui.end_popup()
        Components.end_child()

    @staticmethod
    def image_gallery_with_title(name, folder_path,
                                 display_name=None,
                                 processing_flag=False,
                                 last_add_time=None,
                                 last_add_time_callback=None,
                                 width=0, height=0,
                                 bg_color=(0, 0, 0, 0.1),
                                 right_click_menu_content: Callable[["TextureModule.GalleryTextureInfo", dict[
                                                                                                         str: "TextureModule.GalleryTextureInfo"]], None] = None
                                 ) -> tuple[bool, dict]:
        """
        包括自动更新功能
        title: 标题
        folder_path: 要查找的文件夹
        processing_flag: 是否正在处理，如果为真，则将自动启用add mode
        last_add_time: 上次刷新的时间
        last_add_time_callback: 接受一个参数，修改上次刷新的时间
        """
        try:
            if width == 0:
                width = imgui.get_content_region_available_width()
            if width < 20:
                imgui.text("not enough width")
                return False, {}
            if height == 0:
                height = width / 2.5  # height is the inner gallery height

            columns = 4
            show_names = True

            imgui.push_id(name)
            outer_child_name = f"{name}_outer_child"
            Components.begin_child_auto_height(outer_child_name, border=False, bg_color=bg_color)
            if display_name is None:
                display_name = name
            imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() + g.mImguiStyle.frame_padding[1])
            Components.bold_text(display_name)
            Components.easy_tooltip(folder_path)

            Components.move_to_horizontal_right(2)
            force_update = Components.icon_button('refresh-line', tooltip="Force Update", id=f"force update")

            Components.move_to_horizontal_right(1)
            if Components.icon_button('more-fill', tooltip="More", id=f"image_gallery_more"):
                imgui.open_popup(f"{name}_more")
            if imgui.begin_popup(f"{name}_more"):
                imgui.text(f"more settings for {name} image gallery")
                if imgui.menu_item("View In Explorer")[0]:
                    os.startfile(folder_path)
                imgui.end_popup()

            add_mode = False
            if last_add_time is not None:
                if time.time() - last_add_time > 1:
                    add_mode = processing_flag
                    if last_add_time_callback is not None:
                        last_add_time_callback(time.time())

            thumbnail_info = Components._TextureModule.get_folder_thumbnails(
                folder_path,
                icon_size=max(int(width / columns), 32),
                force_update=force_update,
                add_mode=add_mode
            )  # {name : GalleryTextureInfo}

            if imgui.begin_popup(f"{name}_more"):
                imgui.menu_item(f"Num Files: {len(thumbnail_info)}", enabled=False)
                imgui.end_popup()
            Components.image_gallery(name, folder_path, thumbnail_info,
                                     width=width,
                                     height=height,
                                     columns=columns,
                                     bg_color=bg_color,
                                     show_names=show_names,
                                     right_click_menu_content=right_click_menu_content)
            Components.end_child_auto_height(outer_child_name)

            imgui.pop_id()
            return force_update, thumbnail_info
        except Exception as e:
            Components.error_text(str(e))
            return False, {}

    @staticmethod
    def begin_child(name, width=0.0, height=0.0, border=True, flags=imgui.WINDOW_NONE, bg_color=None):
        if bg_color is not None:
            imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, *bg_color)
        imgui.begin_child(name, width, height, border=border, flags=flags)
        if bg_color is not None:
            imgui.pop_style_color(1)

    @staticmethod
    def end_child():
        imgui.end_child()

    _child_height_data: dict[str: float] = {}
    _child_auto_height_disable_stack: deque = deque()
    _auto_height_child_instant_mode_stack: deque = deque()

    @staticmethod
    def begin_child_auto_height(name, width=0, initial_height=0, border=True, flags=imgui.WINDOW_NO_SCROLLBAR,
                                color=None, bg_color=None, instant_mode=False, disabled=False):
        """
        开启一个自动高度的child
        要结束该child，执行end_child_auto_height

        stack_add default == 1, set to 2 or larger numbers to make animation faster
        """

        if name not in Components._child_height_data:
            Components._child_height_data[
                name] = initial_height if initial_height > 0 else 10 * g.global_scale  # initialize height 不能是0
        curr_height = Components._child_height_data[name]

        if color is not None:
            pos = (imgui.get_cursor_pos()[0] + imgui.get_window_position()[0],
                   imgui.get_cursor_pos()[1] + imgui.get_window_position()[1])
            Components._DrawingModule.draw_rect_filled(pos[0], pos[1], pos[0] + 5 * g.global_scale,
                                                       pos[1] + curr_height,
                                                       col=color, rounding=g.mImguiStyle.child_rounding,
                                                       draw_list_type="window")
        Components._auto_height_child_instant_mode_stack.append(instant_mode)
        Components._child_auto_height_disable_stack.append(disabled)
        if bg_color is not None:
            imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, *bg_color)
        c.begin_child(name, width, curr_height, border, flags)
        if bg_color is not None:
            imgui.pop_style_color(1)

    @staticmethod
    def end_child_auto_height(name):

        fast_mode = Components._auto_height_child_instant_mode_stack.pop()
        disabled = Components._child_auto_height_disable_stack.pop()
        cursor_pos_y = imgui.get_cursor_pos_y()

        if cursor_pos_y > 20:
            _curr_height = Components._child_height_data[name]
            _target_child_height = cursor_pos_y + g.mImguiStyle.window_padding[1]
            height_delta = _target_child_height - _curr_height
            sign = 1.0 if height_delta > 0.0 else -1.0
            abs_delta = abs(height_delta)
            speed = 20 if not fast_mode else 100
            frame_delta = max(1.0, abs_delta) * g.mFrametime * speed  # 最小步进不小于1
            frame_delta = min(abs_delta, frame_delta)  # 如果超过abs_delta， clamp到abs_delta
            _curr_height += frame_delta * sign
            Components._child_height_data[name] = _curr_height

        # CHILD END ============================================================================
        if disabled:
            pos = imgui.get_window_position()
            size = imgui.get_window_size()
            right_bottom = (pos[0] + size[0], pos[1] + size[1])
            Components._DrawingModule.draw_rect_filled(*pos, *right_bottom, color_utils.set_alpha(
                g.mImguiStyle.colors[imgui.COLOR_WINDOW_BACKGROUND], 0.7))

        # endregion
        imgui.end_child()

    @staticmethod
    def quick_menu_item(label, callback=None):
        clicked, state = imgui.menu_item(label)
        if clicked:
            if callback is not None:
                callback()

    @staticmethod
    def file_or_folder_selector(label: str, value: str, width: float = None, is_file: bool = True, disabled=False) -> \
            tuple[bool, str]:
        imgui.push_id(label)
        imgui.push_style_var(imgui.STYLE_ITEM_SPACING,
                             (g.mImguiStyle.item_spacing[0] * 0.5, g.mImguiStyle.item_spacing[1]))
        any_change = False
        if width is None:
            width = imgui.get_content_region_available_width()
        input_text_width = width * 0.66 - g.mImguiStyle.item_spacing[0] - 35 * g.global_scale
        input_text_width = max(20 * g.global_scale, input_text_width)

        imgui.set_next_item_width(input_text_width)
        flag = imgui.INPUT_TEXT_NONE
        if disabled:
            flag |= imgui.INPUT_TEXT_READ_ONLY
        changed, value = Components.input_text('', value, flag)

        # if imgui.is_item_hovered() and len(g.mUserDroppedFiles) > 0:
        #     logging.info(f"file dropped to {label}, {g.mUserDroppedFiles[0]}")
        #     value = g.mUserDroppedFiles[0]
        #     changed = True
        any_change |= changed
        imgui.same_line()
        if imgui.button('...', width=35 * g.global_scale):
            if is_file:
                value = io_utils.open_file_dialog()
            else:
                value = io_utils.open_folder_dialog()
            any_change |= True
        imgui.same_line()
        imgui.text(label)
        imgui.pop_style_var()
        imgui.pop_id()
        return any_change, value

    _imgui_curr_selected_iteration_folder_idx = -1

    @staticmethod
    def move_to_horizontal_right(num_icons):
        imgui.same_line()
        imgui.set_cursor_pos_x(
            imgui.get_cursor_pos_x() + imgui.get_content_region_available_width() - num_icons * (
                    g.mImguiStyle.item_spacing[0] + imgui.get_frame_height())
        )

    @staticmethod
    def move_to_vertical_bottom(num_icons):
        imgui.set_cursor_pos_y(
            imgui.get_cursor_pos_y() + imgui.get_content_region_available()[1] - num_icons * (
                    g.mImguiStyle.item_spacing[1] + imgui.get_frame_height())
        )

    @staticmethod
    def tree_with_numbers(label: str, number: int, indent=0):
        """在tree node 的末尾显示数字"""
        content = f"({number}){''.ljust(indent, ' ')}"
        font_width = imgui.calc_text_size(content)[0]
        frame_width = imgui.get_content_region_available_width()
        opened = imgui.tree_node(label)
        rect_min = imgui.get_item_rect_min()

        Components._DrawingModule.draw_text(rect_min[0] + frame_width - font_width, rect_min[1] - 1,
                                            g.mImguiStyle.colors[imgui.COLOR_TEXT], content, draw_list_type="window")
        return opened

    @classmethod
    def table_template_with_index_and_operation(cls, table_name: str,
                                                objects_set: Iterable, num_objects: int, attrib_names: list[str],
                                                getters: list[Callable[[object], any]],
                                                operation_panel: Callable[[object], None]):
        if num_objects > 10:
            c.begin_child(table_name, 0.0, (imgui.get_frame_height_with_spacing() * 10))
        if imgui.begin_table(table_name, len(attrib_names) + 2, Components.DEFAULT_TABLE_FLAGS):
            imgui.table_setup_column("Index", imgui.TABLE_COLUMN_WIDTH_FIXED, g.font_size * 3)
            for attrib_name in attrib_names:
                imgui.table_setup_column(attrib_name, imgui.TABLE_COLUMN_WIDTH_FIXED, g.font_size * 16)
            imgui.table_setup_column("Operation", imgui.TABLE_COLUMN_WIDTH_FIXED, g.font_size * 5)
            imgui.table_setup_scroll_freeze(0, 1)
            imgui.table_headers_row()
            for i, obj in enumerate(objects_set):
                imgui.push_id(str(i))
                imgui.table_next_column()
                imgui.text(str(i))
                for j in range(len(getters)):
                    imgui.table_next_column()
                    value = getters[j](obj)
                    imgui.text(str(value))
                imgui.table_next_column()
                imgui.button("...")
                if imgui.begin_popup_context_item(None, imgui.POPUP_MOUSE_BUTTON_LEFT):
                    operation_panel(obj)
                    imgui.end_popup()
                imgui.pop_id()
            imgui.end_table()
        if num_objects > 10:
            imgui.end_child()

    @classmethod
    def table_template_with_index(cls, table_name: str, objects_set: Iterable, num_objects: int,
                                  attrib_names: list[str], getters: list[Callable[[object], any]]):
        if num_objects > 10:
            c.begin_child(table_name, 0.0, (imgui.get_frame_height_with_spacing() * 10))
        BASE_CHAR_WIDTH = imgui.calc_text_size("a")[0]
        if imgui.begin_table(table_name, len(attrib_names) + 1, Components.DEFAULT_TABLE_FLAGS):
            imgui.table_setup_column("Index", imgui.TABLE_COLUMN_WIDTH_FIXED, BASE_CHAR_WIDTH * 3)
            for attrib_name in attrib_names:
                imgui.table_setup_column(attrib_name, imgui.TABLE_COLUMN_WIDTH_FIXED, BASE_CHAR_WIDTH * 16)
            imgui.table_setup_scroll_freeze(0, 1)
            imgui.table_headers_row()
            for i, obj in enumerate(objects_set):
                imgui.push_id(str(i))
                imgui.table_next_column()
                imgui.text(str(i))
                for j in range(len(getters)):
                    imgui.table_next_column()
                    value = getters[j](obj)
                    imgui.text(str(value))
                imgui.pop_id()
            imgui.end_table()
        if num_objects > 10:
            imgui.end_child()

    @classmethod
    def info_box(cls, name, content, box_type: Literal['info', 'warning', 'error', 'success'] = "info",
                 custom_color: Optional[tuple] = None, alpha=0.5,
                 right_button_func=None, right_button_icon="caret-right", custom_injection_function=None):
        if custom_color is None:
            if box_type == 'info':
                custom_color = color_utils.set_alpha(Components._StyleModule.COLOR_INFO, alpha)
            elif box_type == 'warning':
                custom_color = color_utils.set_alpha(Components._StyleModule.COLOR_WARNING, alpha)
            elif box_type == 'error':
                custom_color = color_utils.set_alpha(Components._StyleModule.COLOR_DANGER, alpha)
            elif box_type == 'success':
                custom_color = color_utils.set_alpha(Components._StyleModule.COLOR_SUCCESS, alpha)
            else:
                raise Exception(f"Unsupported box_type: {box_type}")
        _wnd_pd = g.mImguiStyle.window_padding
        _wnd_pd_x, _wnd_pd_y = _wnd_pd[0], _wnd_pd[1]

        if right_button_func is not None:
            right_region_width = 25 * g.global_scale
        else:
            right_region_width = 0

        wrap_width = imgui.get_content_region_available_width() - _wnd_pd_x * 2 - right_region_width
        text_size = imgui.calc_text_size(content, False, wrap_width)

        height = text_size[1] + _wnd_pd_y * 2

        single_line_height = imgui.calc_text_size("A")[1]
        if height > single_line_height * 2 + _wnd_pd_y * 2:
            height = single_line_height * 3 + _wnd_pd_y * 2
            show_more = True
        else:
            show_more = False

        imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, *custom_color)
        c.begin_child(name, 0, height, border=False,
                      flags=imgui.WINDOW_NO_SCROLLBAR | imgui.WINDOW_NO_SCROLL_WITH_MOUSE)
        imgui.pop_style_color(1)

        if True:
            imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, 0, 0, 0, 0.0)
            c.begin_child(f"{name}_left", -right_region_width, 0, border=True,
                          flags=imgui.WINDOW_NO_SCROLLBAR | imgui.WINDOW_NO_SCROLL_WITH_MOUSE)
            imgui.pop_style_color(1)

            _wnd_p = imgui.get_window_position()
            _wnd_s = imgui.get_window_size()
            _clip_min = [_wnd_p[0] + _wnd_pd_x, _wnd_p[1] + _wnd_pd_y - 1 * g.global_scale]
            _clip_max = [_wnd_p[0] + _wnd_s[0] - _wnd_pd_x, _wnd_p[1] + _wnd_s[1] - _wnd_pd_y + 1 * g.global_scale]
            if show_more:
                _clip_max[1] -= single_line_height
            imgui.push_clip_rect(*_clip_min, *_clip_max, True)
            imgui.text_wrapped(content)

            imgui.pop_clip_rect()

            if show_more:
                imgui.set_cursor_pos_x(_clip_min[0] - _wnd_p[0])
                imgui.set_cursor_pos_y(_clip_max[1] - _wnd_p[1])
                imgui.push_style_color(imgui.COLOR_TEXT, *Components._StyleModule.COLOR_GRAY)
                c.ctext("... Click to show full content", h_center=True)
                imgui.pop_style_color()

            if show_more:
                if imgui.is_window_hovered() and imgui.is_mouse_clicked(0):
                    imgui.open_popup(f"{name}_popup")
                if imgui.is_popup_open(f"{name}_popup"):
                    _s = imgui.calc_text_size(content, False, 300 * g.global_scale)
                    imgui.set_next_window_size(_s[0] + g.mImguiStyle.window_padding[0] * 2,
                                               _s[1] + g.mImguiStyle.window_padding[1] * 2)

                if imgui.begin_popup(f"{name}_popup"):
                    imgui.text_wrapped(content)
                    imgui.end_popup()

            imgui.end_child()

        if right_region_width > 0:
            imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, 0, 0, 0, 0.1)
            imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (0, 0))
            imgui.same_line()
            c.begin_child(f"{name}_right", 0, 0, border=True,
                          flags=imgui.WINDOW_NO_SCROLLBAR | imgui.WINDOW_NO_SCROLL_WITH_MOUSE)
            imgui.pop_style_var(1)
            imgui.pop_style_color(1)

            _wnd_p = imgui.get_window_position()
            _wnd_s = imgui.get_window_size()
            _icon_size = right_region_width / 1.5
            _x_pad = (_wnd_s[0] - _icon_size) / 2
            _y_pad = (_wnd_s[1] - _icon_size) / 2
            _min_x = _wnd_p[0] + _x_pad
            _min_y = _wnd_p[1] + _y_pad
            _max_x = _wnd_p[0] + _wnd_s[0] - _x_pad
            _max_y = _wnd_p[1] + _wnd_s[1] - _y_pad

            glo, uv0, uv1 = Components._TextureModule.get_icon_glo(right_button_icon)

            if imgui.is_window_hovered():
                if imgui.is_mouse_down(0):
                    col = color_utils.set_alpha(g.mImguiStyle.colors[imgui.COLOR_TEXT], 0.7)
                else:
                    col = g.mImguiStyle.colors[imgui.COLOR_TEXT]
                if imgui.is_mouse_clicked(0) and right_button_func is not None:
                    right_button_func()
            else:
                col = color_utils.set_alpha(g.mImguiStyle.colors[imgui.COLOR_TEXT], 0.5)
            Components._DrawingModule.draw_image(glo, _min_x, _min_y, _max_x, _max_y, uv0, uv1, col=col,
                                                 draw_list_type="window")
            imgui.end_child()

        if custom_injection_function is not None:
            custom_injection_function()

        imgui.end_child()

    @staticmethod
    def _input_text_callback(data: "_ImGuiInputTextCallbackData"):
        if g.mCtrlDown and imgui.is_key_pressed(16):  # Ctrl + A
            data.select_all()
        if g.mCtrlDown and imgui.is_key_pressed(17):  # Ctrl + C
            start = min(data.selection_start, data.selection_end)
            end = max(data.selection_start, data.selection_end)
            buf: bytes = data.buffer.encode('utf-8')[start: end]
            selected_content = buf.decode('utf-8')
            if selected_content:
                pyperclip.copy(str(selected_content))
        if g.mCtrlDown and imgui.is_key_pressed(18):  # Ctrl + V
            content = pyperclip.paste()
            if isinstance(content, str) and content.strip():
                if data.has_selection():
                    start = min(data.selection_start, data.selection_end)
                    end = max(data.selection_start, data.selection_end)
                    data.delete_chars(start, end - start)
                try:
                    data.insert_chars(data.cursor_pos, content)
                except Exception as e:
                    pass

    @staticmethod
    def input_text(label, value, buffer_length=-1, flags=imgui.INPUT_TEXT_NONE):
        flags = flags | imgui.INPUT_TEXT_CALLBACK_ALWAYS
        changed, value = imgui.input_text(label, value, -1, flags, Components._input_text_callback)
        return changed, value

    @staticmethod
    def triple_check_box(label, value):
        any_change = False
        out_value = value
        imgui.push_id(label)
        cg = imgui.radio_button("None", value is None)
        if cg:
            out_value = None
            any_change = True
        imgui.same_line()
        cg = imgui.radio_button("True", value is True)
        if cg:
            out_value = True
            any_change = True
        imgui.same_line()
        cg = imgui.radio_button("False", value is False)
        if cg:
            out_value = False
            any_change = True
        imgui.same_line()
        imgui.text(label)
        imgui.pop_id()
        return any_change, out_value

    _delay_menu_times = {}

    def begin_delay_menu_opened(self, name, enabled=True, delay_time=0.5):
        if name not in Components._delay_menu_times:
            Components._delay_menu_times[name] = 0
        t = Components._delay_menu_times[name]
        opened = False
        if t < delay_time:
            _set_outer_window_focus = False
            imgui.push_style_color(imgui.COLOR_POPUP_BACKGROUND, 0, 0, 0, 0)
            if imgui.begin_menu(name, enabled).opened:
                imgui.dummy(100 * g.global_scale, 1)
                _set_outer_window_focus = True
                t += g.mFrametime
                if imgui.is_mouse_clicked():
                    t += delay_time
                imgui.end_menu()
            imgui.pop_style_color(1)

            if _set_outer_window_focus:
                imgui.set_window_focus()
        else:
            opened = imgui.begin_menu(name, enabled).opened
            if opened:
                t += g.mFrametime
            else:
                t = 0
        Components._delay_menu_times[name] = t
        return opened

    class Toast:
        _toasts = []
        _toasts_to_remove_in_this_frame = set()
        _latest_cursor_pos_y = 0
        _set_toast_window_focus = False

        def __init__(self, name, content, info_type, expire_time=5):
            self.name = name
            self.content = content
            self.info_type = info_type
            self.expire_time = expire_time  # second
            self.current_time = 0.0  # second
            Components.Toast._toasts.append(self)
            # if info_type == "error" or info_type == "warning":
            #     Components.Toast._set_toast_window_focus = True
            self.is_fading = False
            self.fading_percent = 0.0  # 0 to 1
            self.target_position_y = Components.Toast._latest_cursor_pos_y - 20 * g.global_scale
            self.current_position_y = Components.Toast._latest_cursor_pos_y - 20 * g.global_scale

        def t_update(self):
            self.current_time += g.mFrametime
            if self.current_time > self.expire_time:
                self.is_fading = True
                self.fading_percent += g.mFrametime * 0.333
            if self.fading_percent >= 1.0:
                Components.Toast._toasts_to_remove_in_this_frame.add(self)

        def _custom_injection_function_for_info_box(self):
            if imgui.is_window_hovered(imgui.HOVERED_CHILD_WINDOWS):
                self.current_time = 0.0
                self.is_fading = False
                self.fading_percent = 0.0

        def _right_button_func_for_info_box(self):
            Components.Toast._toasts_to_remove_in_this_frame.add(self)

        def t_show(self):
            current_cursor_pos_y = imgui.get_cursor_pos_y()
            self.target_position_y = current_cursor_pos_y
            self.current_position_y += (self.target_position_y - self.current_position_y) * min(1.0,
                                                                                                g.mFrametime * 30.0)
            imgui.set_cursor_pos_y(self.current_position_y)

            alpha = 1 - self.fading_percent
            Components.info_box(self.name, self.content, self.info_type, alpha=alpha,
                                custom_injection_function=self._custom_injection_function_for_info_box,
                                right_button_func=self._right_button_func_for_info_box, right_button_icon="charm_cross")

        @classmethod
        def update_toasts(cls):
            """ run this function in Toast Window.update"""
            for toast in cls._toasts:
                toast.t_update()
            while len(cls._toasts_to_remove_in_this_frame) > 0:
                toast = cls._toasts_to_remove_in_this_frame.pop()
                cls._toasts.remove(toast)

        @classmethod
        def show_toasts(cls):
            """ run this function in Toast Window.content"""
            if cls._set_toast_window_focus:
                imgui.set_window_focus()
                cls._set_toast_window_focus = False
            for toast in cls._toasts:
                toast.t_show()
            Components.Toast._latest_cursor_pos_y = imgui.get_cursor_pos_y()

    @staticmethod
    def toast(content, info_type: Literal['info', 'warning', 'error', 'success'] = "info", expire_time=5):
        name = str(uuid.uuid4())
        return Components.Toast(name, content, info_type, expire_time)

    class ToastLogHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.setLevel(logging.WARNING)  # 只处理WARNING及以上级别

        def emit(self, record):
            try:
                message = self.format(record)
                if record.levelno >= logging.ERROR:
                    info_type = 'error'
                elif record.levelno >= logging.WARNING:
                    info_type = 'warning'
                else:
                    return  # 其他级别不处理

                # 使用线程安全的方式调用UI方法（假设在主线程执行）
                Components.toast(
                    content=message,
                    info_type=info_type,
                    expire_time=5
                )
            except Exception as e:
                logging.error(f"ToastLogHandler failed: {str(e)}")

    # 配置日志处理器
    toast_handler = ToastLogHandler()
    toast_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))

    @staticmethod
    def add_toast_handler(logger):
        logger.addHandler(Components.toast_handler)


c = Components()
