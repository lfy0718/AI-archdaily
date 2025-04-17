# region Level 0
while True:
    from dev.modules.base_module import BaseModule

    break
# endregion

# region Level 1
while True:
    from dev.modules.style_module import StyleModule
    from dev.modules.texture_module import TextureModule
    # from dev.modules.event_module import EventModule

    break
# endregion
# region Level 1
while True:
    # from dev.modules.animation_module import AnimationModule
    # from dev.modules.chart_module import ChartModule
    # from dev.modules.cursor_module import CursorModule
    from dev.modules.drawing_module import DrawingModule, DrawListTypes
    from dev.modules.font_module import FontModule
    from dev.modules.graphic_module import GraphicModule
    # from dev.modules.language_module import LanguageModule
    # from dev.modules.layout_module import LayoutModule
    # from dev.modules.shadow_module import ShadowModule

    break
# endregion

# NOTE: Add new modules to ALL_MODULES
ALL_MODULES = [
    StyleModule,
    # LayoutModule,
    # EventModule,
    DrawingModule,
    # CursorModule,
    # ShadowModule,
    # AnimationModule,
    TextureModule,
    GraphicModule,
    FontModule,
    # ChartModule,
    # LanguageModule,
]
