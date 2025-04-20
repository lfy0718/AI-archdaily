from contextlib import contextmanager

import imgui

from dev.global_app_state import g
from dev.modules.base_module import BaseModule
from dev.utils import color_utils


class StyleModule(BaseModule):
    # region colors
    COLOR_LIGHT_GRAY = (0.7, 0.7, 0.7, 1.0)
    COLOR_GRAY = (0.5, 0.5, 0.5, 1.0)
    COLOR_DARK_GRAY = (0.25, 0.25, 0.25, 1.0)
    COLOR_WHITE = (1.0, 1.0, 1.0, 1.0)
    COLOR_BLACK = (0.0, 0.0, 0.0, 1.0)
    COLOR_BLUE = (0.18, 0.38, 0.63, 1.0)
    COLOR_LIGHT_BLUE = (0.6, 0.8, 1.0, 1.0)
    COLOR_GREEN = (0.1, 0.6, 0.3, 1.0)
    COLOR_YELLOW = (0.9, 0.7, 0.1, 1.0)
    COLOR_RED = (0.65, 0.2, 0.2, 1.0)
    COLOR_PINK = (0.9, 0.7, 0.8, 1.0)  # 粉色
    COLOR_ORANGE = (0.8, 0.6, 0.4, 1.0)  # 橙色
    COLOR_PURPLE = (0.5, 0.3, 0.6, 1.0)  # 紫色
    COLOR_BROWN = (0.5, 0.35, 0.3, 1.0)  # 棕色
    COLOR_CYAN = (0.1, 0.7, 0.8, 1.0)  # 青色
    COLOR_MAGENTA = (0.8, 0.2, 0.6, 1.0)  # 洋红色
    COLOR_LIME = (0.4, 0.8, 0.4, 1.0)  # 酸橙绿
    COLOR_GOLD = (0.8, 0.7, 0.4, 1.0)  # 金色
    COLOR_SILVER = (0.65, 0.65, 0.65, 1.0)  # 银色
    COLOR_MAROON = (0.4, 0.2, 0.2, 1.0)  # 栗色
    COLOR_NAVY = (0.1, 0.2, 0.4, 1.0)  # 海军蓝
    COLOR_TURQUOISE = (0.2, 0.7, 0.7, 1.0)  # 青绿色
    COLOR_VIOLET = (0.7, 0.4, 0.7, 1.0)  # 紫罗兰色
    COLOR_INDIGO = (0.2, 0.1, 0.4, 1.0)  # 靛蓝色
    COLOR_OLIVE = (0.5, 0.5, 0.2, 1.0)  # 橄榄色

    COLOR_PRIMARY = COLOR_BLUE
    COLOR_SECONDARY = COLOR_GRAY
    COLOR_SUCCESS = COLOR_GREEN
    COLOR_INFO = COLOR_BLUE
    COLOR_WARNING = COLOR_YELLOW
    COLOR_DANGER = COLOR_RED
    COLOR_DISABLED = COLOR_DARK_GRAY
    COLOR_DARK_WINDOW_BACKGROUND = (0, 0, 0, 0)

    COLOR_PRIMARY_LIGHTENED = color_utils.lighten_color(COLOR_PRIMARY, 0.1)
    COLOR_DANGER_LIGHTENED = color_utils.lighten_color(COLOR_DANGER, 0.1)

    COLOR_CHILD_BG = (0, 0, 0, 0.05)
    # endregion
    _imgui_color_key_to_name = {
        0: "COLOR_TEXT",
        1: "COLOR_TEXT_DISABLED",
        2: "COLOR_WINDOW_BACKGROUND",
        3: "COLOR_CHILD_BACKGROUND",
        4: "COLOR_POPUP_BACKGROUND",
        5: "COLOR_BORDER",
        6: "COLOR_BORDER_SHADOW",
        7: "COLOR_FRAME_BACKGROUND",
        8: "COLOR_FRAME_BACKGROUND_HOVERED",
        9: "COLOR_FRAME_BACKGROUND_ACTIVE",
        10: "COLOR_TITLE_BACKGROUND",
        11: "COLOR_TITLE_BACKGROUND_ACTIVE",
        12: "COLOR_TITLE_BACKGROUND_COLLAPSED",
        13: "COLOR_MENUBAR_BACKGROUND",
        14: "COLOR_SCROLLBAR_BACKGROUND",
        15: "COLOR_SCROLLBAR_GRAB",
        16: "COLOR_SCROLLBAR_GRAB_HOVERED",
        17: "COLOR_SCROLLBAR_GRAB_ACTIVE",
        18: "COLOR_CHECK_MARK",
        19: "COLOR_SLIDER_GRAB",
        20: "COLOR_SLIDER_GRAB_ACTIVE",
        21: "COLOR_BUTTON",
        22: "COLOR_BUTTON_HOVERED",
        23: "COLOR_BUTTON_ACTIVE",
        24: "COLOR_HEADER",
        25: "COLOR_HEADER_HOVERED",
        26: "COLOR_HEADER_ACTIVE",
        27: "COLOR_SEPARATOR",
        28: "COLOR_SEPARATOR_HOVERED",
        29: "COLOR_SEPARATOR_ACTIVE",
        30: "COLOR_RESIZE_GRIP",
        31: "COLOR_RESIZE_GRIP_HOVERED",
        32: "COLOR_RESIZE_GRIP_ACTIVE",
        33: "COLOR_TAB",
        34: "COLOR_TAB_HOVERED",
        35: "COLOR_TAB_ACTIVE",
        36: "COLOR_TAB_UNFOCUSED",
        37: "COLOR_TAB_UNFOCUSED_ACTIVE",
        38: "COLOR_PLOT_LINES",
        39: "COLOR_PLOT_LINES_HOVERED",
        40: "COLOR_PLOT_HISTOGRAM",
        41: "COLOR_PLOT_HISTOGRAM_HOVERED",
        42: "COLOR_TABLE_HEADER_BACKGROUND",
        43: "COLOR_TABLE_BORDER_STRONG",
        44: "COLOR_TABLE_BORDER_LIGHT",
        45: "COLOR_TABLE_ROW_BACKGROUND",
        46: "COLOR_TABLE_ROW_BACKGROUND_ALT",
        47: "COLOR_TEXT_SELECTED_BACKGROUND",
        48: "COLOR_DRAG_DROP_TARGET",
        49: "COLOR_NAV_HIGHLIGHT",
        50: "COLOR_NAV_WINDOWING_HIGHLIGHT",
        51: "COLOR_NAV_WINDOWING_DIM_BACKGROUND",
        52: "COLOR_MODAL_WINDOW_DIM_BACKGROUND",
        # 53: "COLOR_COUNT"
    }

    @classmethod
    def m_init(cls):
        super().m_init()

        style: imgui.core.GuiStyle = imgui.get_style()
        g.mImguiStyle = style

        cls._init_light_mode()
        cls._init_imgui_style()

    @classmethod
    def _init_dark_mode(cls):
        style = g.mImguiStyle
        style.colors[imgui.COLOR_TEXT] = (1.00, 1.00, 1.00, 1.00)
        style.colors[imgui.COLOR_TEXT_DISABLED] = (0.50, 0.50, 0.50, 1.00)
        style.colors[imgui.COLOR_WINDOW_BACKGROUND] = (0.12, 0.12, 0.12, 1.00)
        style.colors[imgui.COLOR_CHILD_BACKGROUND] = (0.00, 0.00, 0.00, 0.00)
        style.colors[imgui.COLOR_POPUP_BACKGROUND] = (0.12, 0.12, 0.12, 1.00)
        style.colors[imgui.COLOR_BORDER] = (0.12, 0.12, 0.12, 0.00)
        style.colors[imgui.COLOR_BORDER_SHADOW] = (0.00, 0.00, 0.00, 0.00)
        style.colors[imgui.COLOR_FRAME_BACKGROUND] = (0.32, 0.32, 0.32, 0.50)
        style.colors[imgui.COLOR_FRAME_BACKGROUND_HOVERED] = (0.67, 0.67, 0.67, 0.40)
        style.colors[imgui.COLOR_FRAME_BACKGROUND_ACTIVE] = (0.98, 0.98, 0.98, 0.67)
        style.colors[imgui.COLOR_TITLE_BACKGROUND] = (0.12, 0.12, 0.12, 1.00)
        style.colors[imgui.COLOR_TITLE_BACKGROUND_ACTIVE] = (0.23, 0.23, 0.23, 1.00)
        style.colors[imgui.COLOR_TITLE_BACKGROUND_COLLAPSED] = (0.00, 0.00, 0.00, 0.51)
        style.colors[imgui.COLOR_MENUBAR_BACKGROUND] = (0.14, 0.14, 0.14, 1.00)
        style.colors[imgui.COLOR_SCROLLBAR_BACKGROUND] = (0.02, 0.02, 0.02, 0.53)
        style.colors[imgui.COLOR_SCROLLBAR_GRAB] = (0.31, 0.31, 0.31, 1.00)
        style.colors[imgui.COLOR_SCROLLBAR_GRAB_HOVERED] = (0.41, 0.41, 0.41, 1.00)
        style.colors[imgui.COLOR_SCROLLBAR_GRAB_ACTIVE] = (0.51, 0.51, 0.51, 1.00)
        style.colors[imgui.COLOR_CHECK_MARK] = (0.26, 0.59, 0.98, 1.00)
        style.colors[imgui.COLOR_SLIDER_GRAB] = (0.24, 0.52, 0.88, 1.00)
        style.colors[imgui.COLOR_SLIDER_GRAB_ACTIVE] = (0.26, 0.59, 0.98, 1.00)
        style.colors[imgui.COLOR_BUTTON] = (0.32, 0.32, 0.32, 1.00)
        style.colors[imgui.COLOR_BUTTON_HOVERED] = (0.40, 0.40, 0.40, 1.00)
        style.colors[imgui.COLOR_BUTTON_ACTIVE] = (0.35, 0.35, 0.35, 1.00)
        style.colors[imgui.COLOR_HEADER] = (0.30, 0.30, 0.30, 1.00)
        style.colors[imgui.COLOR_HEADER_HOVERED] = (0.46, 0.46, 0.46, 1.00)
        style.colors[imgui.COLOR_HEADER_ACTIVE] = (0.44, 0.44, 0.44, 1.00)
        style.colors[imgui.COLOR_SEPARATOR] = (0.39, 0.39, 0.39, 0.50)
        style.colors[imgui.COLOR_SEPARATOR_HOVERED] = (0.10, 0.40, 0.75, 0.78)
        style.colors[imgui.COLOR_SEPARATOR_ACTIVE] = (0.10, 0.40, 0.75, 1.00)
        style.colors[imgui.COLOR_RESIZE_GRIP] = (0.26, 0.59, 0.98, 0.20)
        style.colors[imgui.COLOR_RESIZE_GRIP_HOVERED] = (0.26, 0.59, 0.98, 0.67)
        style.colors[imgui.COLOR_RESIZE_GRIP_ACTIVE] = (0.26, 0.59, 0.98, 0.95)
        style.colors[imgui.COLOR_TAB] = (0.33, 0.33, 0.33, 1.00)
        style.colors[imgui.COLOR_TAB_HOVERED] = (0.46, 0.46, 0.46, 1.00)
        style.colors[imgui.COLOR_TAB_ACTIVE] = (0.20, 0.41, 0.68, 1.00)
        style.colors[imgui.COLOR_TAB_UNFOCUSED] = (0.07, 0.10, 0.15, 0.97)
        style.colors[imgui.COLOR_TAB_UNFOCUSED_ACTIVE] = (0.14, 0.26, 0.42, 1.00)
        style.colors[imgui.COLOR_PLOT_LINES] = (0.61, 0.61, 0.61, 1.00)
        style.colors[imgui.COLOR_PLOT_LINES_HOVERED] = (1.00, 0.43, 0.35, 1.00)
        style.colors[imgui.COLOR_PLOT_HISTOGRAM] = (0.24, 0.52, 0.88, 1.00)
        style.colors[imgui.COLOR_PLOT_HISTOGRAM_HOVERED] = (1.00, 0.60, 0.00, 1.00)
        style.colors[imgui.COLOR_TABLE_HEADER_BACKGROUND] = (0.19, 0.19, 0.20, 1.00)
        style.colors[imgui.COLOR_TABLE_BORDER_STRONG] = (0.31, 0.31, 0.35, 1.00)
        style.colors[imgui.COLOR_TABLE_BORDER_LIGHT] = (0.23, 0.23, 0.25, 1.00)
        style.colors[imgui.COLOR_TABLE_ROW_BACKGROUND] = (0.00, 0.00, 0.00, 0.00)
        style.colors[imgui.COLOR_TABLE_ROW_BACKGROUND_ALT] = (1.00, 1.00, 1.00, 0.06)
        style.colors[imgui.COLOR_TEXT_SELECTED_BACKGROUND] = (0.26, 0.59, 0.98, 0.35)
        style.colors[imgui.COLOR_DRAG_DROP_TARGET] = (1.00, 1.00, 0.00, 0.90)
        style.colors[imgui.COLOR_NAV_HIGHLIGHT] = (0.26, 0.59, 0.98, 1.00)
        style.colors[imgui.COLOR_NAV_WINDOWING_HIGHLIGHT] = (1.00, 1.00, 1.00, 0.70)
        style.colors[imgui.COLOR_NAV_WINDOWING_DIM_BACKGROUND] = (0.80, 0.80, 0.80, 0.20)
        style.colors[imgui.COLOR_MODAL_WINDOW_DIM_BACKGROUND] = (0.09, 0.09, 0.09, 0.89)

        cls.COLOR_PRIMARY = cls.COLOR_BLUE
        cls.COLOR_SECONDARY = cls.COLOR_GRAY
        cls.COLOR_SUCCESS = cls.COLOR_GREEN
        cls.COLOR_WARNING = cls.COLOR_YELLOW
        cls.COLOR_DANGER = cls.COLOR_RED
        cls.COLOR_DISABLED = cls.COLOR_DARK_GRAY
        cls.COLOR_DARK_WINDOW_BACKGROUND = color_utils.darken_color(style.colors[imgui.COLOR_WINDOW_BACKGROUND], 0.1)
        cls.COLOR_PRIMARY_LIGHTENED = color_utils.lighten_color(cls.COLOR_PRIMARY, 0.1)
        cls.COLOR_DANGER_LIGHTENED = color_utils.lighten_color(cls.COLOR_DANGER, 0.1)

    @classmethod
    def _init_light_mode(cls):
        style = g.mImguiStyle
        style.colors[imgui.COLOR_TEXT] = (0.00, 0.00, 0.00, 1.00)
        style.colors[imgui.COLOR_TEXT_DISABLED] = (0.50, 0.50, 0.50, 1.00)
        style.colors[imgui.COLOR_WINDOW_BACKGROUND] = (1.00, 1.00, 1.00, 1.00)
        style.colors[imgui.COLOR_CHILD_BACKGROUND] = (1.00, 1.00, 1.00, 0.00)
        style.colors[imgui.COLOR_POPUP_BACKGROUND] = (0.94, 0.94, 0.94, 1.00)
        style.colors[imgui.COLOR_BORDER] = (0.78, 0.78, 0.78, 0.39)
        style.colors[imgui.COLOR_BORDER_SHADOW] = (0.00, 0.00, 0.00, 0.00)
        style.colors[imgui.COLOR_FRAME_BACKGROUND] = (0.89, 0.89, 0.89, 1.00)
        style.colors[imgui.COLOR_FRAME_BACKGROUND_HOVERED] = (0.85, 0.85, 0.85, 1.00)
        style.colors[imgui.COLOR_FRAME_BACKGROUND_ACTIVE] = (0.74, 0.80, 0.87, 1.00)
        style.colors[imgui.COLOR_TITLE_BACKGROUND] = (0.94, 0.94, 0.94, 1.00)
        style.colors[imgui.COLOR_TITLE_BACKGROUND_ACTIVE] = (0.82, 0.82, 0.82, 1.00)
        style.colors[imgui.COLOR_TITLE_BACKGROUND_COLLAPSED] = (1.00, 1.00, 1.00, 0.51)
        style.colors[imgui.COLOR_MENUBAR_BACKGROUND] = (1.00, 1.00, 1.00, 1.00)
        style.colors[imgui.COLOR_SCROLLBAR_BACKGROUND] = (0.97, 0.97, 0.97, 1.00)
        style.colors[imgui.COLOR_SCROLLBAR_GRAB] = (0.81, 0.81, 0.81, 1.00)
        style.colors[imgui.COLOR_SCROLLBAR_GRAB_HOVERED] = (0.41, 0.41, 0.41, 1.00)
        style.colors[imgui.COLOR_SCROLLBAR_GRAB_ACTIVE] = (0.51, 0.51, 0.51, 1.00)
        style.colors[imgui.COLOR_CHECK_MARK] = (0.26, 0.59, 0.98, 1.00)
        style.colors[imgui.COLOR_SLIDER_GRAB] = (0.24, 0.52, 0.88, 1.00)
        style.colors[imgui.COLOR_SLIDER_GRAB_ACTIVE] = (0.26, 0.59, 0.98, 1.00)
        style.colors[imgui.COLOR_BUTTON] = (0.80, 0.80, 0.80, 1.00)
        style.colors[imgui.COLOR_BUTTON_HOVERED] = (0.74, 0.80, 0.87, 1.00)
        style.colors[imgui.COLOR_BUTTON_ACTIVE] = (0.63, 0.70, 0.78, 1.00)
        style.colors[imgui.COLOR_HEADER] = (0.84, 0.84, 0.84, 1.00)
        style.colors[imgui.COLOR_HEADER_HOVERED] = (0.74, 0.80, 0.87, 1.00)
        style.colors[imgui.COLOR_HEADER_ACTIVE] = (0.63, 0.70, 0.78, 1.00)
        style.colors[imgui.COLOR_SEPARATOR] = (0.64, 0.64, 0.64, 0.50)
        style.colors[imgui.COLOR_SEPARATOR_HOVERED] = (0.10, 0.40, 0.75, 0.78)
        style.colors[imgui.COLOR_SEPARATOR_ACTIVE] = (0.10, 0.40, 0.75, 1.00)
        style.colors[imgui.COLOR_RESIZE_GRIP] = (0.49, 0.49, 0.49, 0.20)
        style.colors[imgui.COLOR_RESIZE_GRIP_HOVERED] = (0.71, 0.71, 0.71, 0.67)
        style.colors[imgui.COLOR_RESIZE_GRIP_ACTIVE] = (0.45, 0.45, 0.45, 0.95)
        style.colors[imgui.COLOR_TAB] = (0.84, 0.84, 0.84, 1.00)
        style.colors[imgui.COLOR_TAB_HOVERED] = (0.74, 0.80, 0.87, 1.00)
        style.colors[imgui.COLOR_TAB_ACTIVE] = (0.63, 0.70, 0.78, 1.00)
        style.colors[imgui.COLOR_TAB_UNFOCUSED] = (0.07, 0.10, 0.15, 0.97)
        style.colors[imgui.COLOR_TAB_UNFOCUSED_ACTIVE] = (0.14, 0.26, 0.42, 1.00)
        style.colors[imgui.COLOR_PLOT_LINES] = (0.61, 0.61, 0.61, 1.00)
        style.colors[imgui.COLOR_PLOT_LINES_HOVERED] = (1.00, 0.43, 0.35, 1.00)
        style.colors[imgui.COLOR_PLOT_HISTOGRAM] = (0.63, 0.70, 0.78, 1.00)
        style.colors[imgui.COLOR_PLOT_HISTOGRAM_HOVERED] = (0.63, 0.70, 0.78, 1.00)
        style.colors[imgui.COLOR_TABLE_HEADER_BACKGROUND] = (0.88, 0.88, 0.88, 1.00)
        style.colors[imgui.COLOR_TABLE_BORDER_STRONG] = (0.73, 0.73, 0.73, 1.00)
        style.colors[imgui.COLOR_TABLE_BORDER_LIGHT] = (0.93, 0.93, 0.93, 1.00)
        style.colors[imgui.COLOR_TABLE_ROW_BACKGROUND] = (1.00, 1.00, 1.00, 0.00)
        style.colors[imgui.COLOR_TABLE_ROW_BACKGROUND_ALT] = (1.00, 1.00, 1.00, 0.06)
        style.colors[imgui.COLOR_TEXT_SELECTED_BACKGROUND] = (0.26, 0.59, 0.98, 0.35)
        style.colors[imgui.COLOR_DRAG_DROP_TARGET] = (1.00, 1.00, 0.00, 0.90)
        style.colors[imgui.COLOR_NAV_HIGHLIGHT] = (0.26, 0.59, 0.98, 1.00)
        style.colors[imgui.COLOR_NAV_WINDOWING_HIGHLIGHT] = (1.00, 1.00, 1.00, 0.70)
        style.colors[imgui.COLOR_NAV_WINDOWING_DIM_BACKGROUND] = (0.80, 0.80, 0.80, 0.20)
        style.colors[imgui.COLOR_MODAL_WINDOW_DIM_BACKGROUND] = (0.71, 0.71, 0.71, 0.66)

        cls.COLOR_PRIMARY = cls.COLOR_LIGHT_BLUE
        cls.COLOR_SECONDARY = cls.COLOR_GRAY
        cls.COLOR_SUCCESS = cls.COLOR_GREEN
        cls.COLOR_WARNING = cls.COLOR_YELLOW
        cls.COLOR_DANGER = color_utils.lighten_color(cls.COLOR_RED, 0.2)
        cls.COLOR_DISABLED = cls.COLOR_LIGHT_GRAY
        cls.COLOR_DARK_WINDOW_BACKGROUND = color_utils.darken_color(style.colors[imgui.COLOR_WINDOW_BACKGROUND], 0.1)
        cls.COLOR_PRIMARY_LIGHTENED = color_utils.lighten_color(cls.COLOR_PRIMARY, 0.1)
        cls.COLOR_DANGER_LIGHTENED = color_utils.lighten_color(cls.COLOR_DANGER, 0.1)

    @classmethod
    def _init_imgui_style(cls):
        style = g.mImguiStyle
        style.window_rounding = round(8 * g.global_scale)
        style.child_rounding = round(4 * g.global_scale)
        style.frame_rounding = round(4 * g.global_scale)
        style.popup_rounding = round(8 * g.global_scale)
        style.tab_rounding = round(4 * g.global_scale)
        style.scrollbar_rounding = round(9 * g.global_scale)
        style.grab_rounding = round(0 * g.global_scale)

        style.window_padding = (8 * g.global_scale, 8 * g.global_scale)
        style.frame_padding = (4 * g.global_scale, 4 * g.global_scale)
        style.cell_padding = (4 * g.global_scale, 2 * g.global_scale)

        style.item_spacing = (10 * g.global_scale, 10 * g.global_scale)
        style.indent_spacing = 21 * g.global_scale
        style.item_inner_spacing = (4 * g.global_scale, 4 * g.global_scale)

        style.window_title_align = (0.5, 0.5)

    @classmethod
    def copy_current_color_style_to_clipboard(cls):
        import pyperclip
        lines = ["style = g.mImguiStyle"]
        style = g.mImguiStyle
        for key, name in cls._imgui_color_key_to_name.items():
            color = style.colors[key]
            color_str = ", ".join(f"{round(num, 2):.2f}" for num in color)
            line = f"style.colors[imgui.{name}] = ({color_str})"
            lines.append(line)
        code = "\n".join(lines)
        pyperclip.copy(code)

    @classmethod
    def push_highlighted_button_color(cls):
        color = color_utils.align_alpha(cls.COLOR_PRIMARY, g.mImguiStyle.colors[imgui.COLOR_BUTTON])
        lighten_color = color_utils.align_alpha(cls.COLOR_PRIMARY_LIGHTENED, g.mImguiStyle.colors[imgui.COLOR_BUTTON])

        imgui.push_style_color(imgui.COLOR_BUTTON, *color)
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, *lighten_color)
        imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, *color)

    @classmethod
    def push_dangerous_button_color(cls):
        color = color_utils.align_alpha(cls.COLOR_DANGER, g.mImguiStyle.colors[imgui.COLOR_BUTTON])
        lighten_color = color_utils.align_alpha(cls.COLOR_DANGER_LIGHTENED, g.mImguiStyle.colors[imgui.COLOR_BUTTON])

        imgui.push_style_color(imgui.COLOR_BUTTON, *color)
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, *lighten_color)
        imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, *color)

    @classmethod
    def push_disabled_button_color(cls):
        color = color_utils.align_alpha(cls.COLOR_DISABLED, g.mImguiStyle.colors[imgui.COLOR_BUTTON])
        imgui.push_style_color(imgui.COLOR_BUTTON, *color)
        imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, *color)
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, *color)

    @classmethod
    def pop_button_color(cls):
        imgui.pop_style_color(3)


    @classmethod
    def push_loose_padding(cls):
        imgui.push_style_var(imgui.STYLE_FRAME_PADDING,
                             (round(g.mImguiStyle.frame_padding[0] * 1.5), round(g.mImguiStyle.frame_padding[1] * 1.5)))

    @classmethod
    def pop_loose_padding(cls):
        imgui.pop_style_var(1)
