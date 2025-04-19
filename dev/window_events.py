import imgui
import moderngl_window as mglw
from moderngl_window.integrations.imgui import ModernglWindowRenderer

from config import *
from dev import modules
from dev.components import c
from dev.global_app_state import g
from dev.modules import FontModule
from dev.windows import WindowManager


class WindowEvents(mglw.WindowConfig):
    # SOME SETTINGS FOR WINDOW
    gl_version = (3, 3)  # use opengl 4.2
    title = PROJECT_NAME
    aspect_ratio = None
    vsync = True
    log_level = logging.INFO  # set moderngl log level
    resource_dir = RESOURCES_DIR
    clear_color = (0.8, 0.8, 0.8, 1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Uncomment the next line in the release version to disable the ESC exit functionality.
        # self.wnd.exit_key = None

        # Create context
        imgui.create_context()

        # Init global app state
        g.mFirstLoop = True
        g.mWindowEvent = self
        g.mWindowSize = self.wnd.size

        # font should be created before ModernglWindowRenderer(self.wnd)
        FontModule.m_create_fonts()
        self.imgui = ModernglWindowRenderer(self.wnd)  # create imgui renderer after all modules are inited
        # Init Modules and windows
        for module in modules.ALL_MODULES:
            module.m_init()
        c.c_init()
        WindowManager.w_init()

        # Scroll
        self.target_scroll_y = 0.0

        # We put the full-screen handling in the __init__ instead of using class static variables to
        # prevent issues with window scaling when specifying full-screen at the beginning and exiting full-screen.
        # This may be due to a lack of comprehensive understanding of how to use the moderngl window.
        # However, the approach used here does indeed solve the problem.
        # if user_settings.fullscreen:
        #     self.wnd.fullscreen = True

    def render(self, time: float, frametime: float):
        """
        Main loop
        This is the main loop function specified by the moderngl window.
        We have divided it into three parts: update, render_ui, and late_update.
        update and late_update mainly handle logic,
        while render_ui is responsible for generating and rendering UI components.
        """
        # 1. logical update
        # The main logic for handling operations in the update method involves other non-Imgui graphical rendering.
        self._update(time, frametime)

        # 2. ui rendering
        # This function is mainly responsible for rendering the ImGui interface.
        self._render_ui()

        # 3. the late logical update
        # The late update invokes after all rendering tasks are completed.
        self._late_update()

    def _update(self, time: float, frametime: float):
        """
        Logical update
        """
        # 0. UPDATE GLOBAL APP STATE
        g.mCurrentAppStage = g.AppStage.Update
        g.mTime = time
        g.mFrametime = max(frametime, 1e-5)  # mFrametime should not be zero

        # 1. UPDATE
        c.c_update()
        WindowManager.w_update()

        # 2. MISC
        # handle smooth scroll
        self._handle_smooth_scroll(frametime)

        # 3. Clean Up
        g.mCurrentAppStage = g.AppStage.Undefined

    def _render_ui(self):
        """
        Render the UI
        """
        # 0. Update Global App State
        g.mCurrentAppStage = g.AppStage.RenderUI

        # 1. CREATE NEW IMGUI FRAME
        imgui.new_frame()

        # 2. GENERATE UI ELEMENTS

        WindowManager.w_render()

        # 3. render to ctx.screen
        self.wnd.use(), imgui.render(), self.imgui.render(imgui.get_draw_data())

        # 4. Clean Up
        g.mCurrentAppStage = g.AppStage.Undefined

    def _late_update(self):
        """
        Late update function
        """
        _ = self

        # 0. Update Global App State
        g.mCurrentAppStage = g.AppStage.LateUpdate

        # 1. UPDATE MANAGERS
        c.c_late_update()
        WindowManager.w_late_update()

        # 2. UPDATE GLOBAL APP STATE
        g.mFirstLoop = False

        # 3. Clean Up
        g.mCurrentAppStage = g.AppStage.Undefined

    # region Events

    def resize(self, width: int, height: int):
        g.mWindowSize = self.wnd.size
        self.imgui.resize(width, height)

    def key_event(self, key, action, modifiers):
        self.imgui.key_event(key, action, modifiers)
        if action == "ACTION_PRESS":
            if key == 65505:
                g.mShiftDown = True
                return
            elif key == 65507:
                g.mCtrlDown = True
                return

        elif action == "ACTION_RELEASE":
            if key == 65505:
                g.mShiftDown = False
                return
            if key == 65507:
                g.mCtrlDown = False
                return

    def mouse_position_event(self, x, y, dx, dy):
        self.imgui.mouse_position_event(x, y, dx, dy)

    def mouse_drag_event(self, x, y, dx, dy):
        self.imgui.mouse_drag_event(x, y, dx, dy)

    def mouse_scroll_event(self, x_offset, y_offset):
        self.target_scroll_y += y_offset  # handle mouse smooth scroll event in update

    def mouse_press_event(self, x, y, button):
        self.imgui.mouse_press_event(x, y, button)

    def mouse_release_event(self, x: int, y: int, button: int):
        self.imgui.mouse_release_event(x, y, button)

    def unicode_char_entered(self, char):
        self.imgui.unicode_char_entered(char)

    # endregion Events

    def _handle_smooth_scroll(self, frametime):
        # handle mouse scroll event
        if abs(self.target_scroll_y) < 0.15:
            self.target_scroll_y = 0.0
        percent = min(8.0 * frametime, 1.0)
        delta_y = self.target_scroll_y * percent
        self.target_scroll_y -= delta_y
        self.imgui.mouse_scroll_event(0, delta_y)

    @classmethod
    def run(cls, args=None, timer=None, **kwargs):
        """
        overrides WindowEvents.run()
        """
        g.mCurrentAppStage = g.AppStage.Prepare
        g.mHasEmbedKernel = ("embed_kernel_mode" in kwargs) and (kwargs["embed_kernel_mode"])

        logging.info(f"[{cls.__name__}] Invoking {cls.__name__}.run()")
        logging.info(f"[{cls.__name__}] Loading modules")
        from moderngl_window import setup_basic_logging, create_parser, parse_args, get_local_window_cls, \
            activate_context
        from moderngl_window.timers.clock import Timer
        import weakref
        setup_basic_logging(cls.log_level)
        parser = create_parser()
        cls.add_arguments(parser)
        values = parse_args(args=args, parser=parser)
        cls.argv = values
        window_cls = get_local_window_cls(values.window)
        # Calculate window size
        size = values.size or cls.window_size
        size = int(size[0] * values.size_mult), int(size[1] * values.size_mult)
        # Resolve cursor
        show_cursor = values.cursor
        if show_cursor is None:
            show_cursor = cls.cursor
        window = window_cls(
            title=cls.title,
            size=size,
            fullscreen=cls.fullscreen or values.fullscreen,
            resizable=values.resizable
            if values.resizable is not None
            else cls.resizable,
            gl_version=cls.gl_version,
            aspect_ratio=cls.aspect_ratio,
            vsync=values.vsync if values.vsync is not None else cls.vsync,
            samples=values.samples if values.samples is not None else cls.samples,
            cursor=show_cursor if show_cursor is not None else True,
            backend=values.backend,
        )
        window.print_context_info()
        activate_context(window=window)
        timer = timer or Timer()
        config = cls(ctx=window.ctx, wnd=window, timer=timer)
        # Avoid the event assigning in the property setter for now
        # We want the even assigning to happen in WindowConfig.__init__
        # so users are free to assign them in their own __init__.
        window._config = weakref.ref(config)

        # Swap buffers once before staring the main loop.
        # This can trigger additional resize events reporting
        # a more accurate buffer size
        window.swap_buffers()
        window.set_default_viewport()

        timer.start()
        logging.info(f"[{cls.__name__}] Start rendering loop")
        while not window.is_closing:
            g.mCurrentAppStage = g.AppStage.MainLoop

            current_time, delta = timer.next_frame()

            if config.clear_color is not None:
                window.clear(*config.clear_color)

            # Always bind the window framebuffer before calling render
            window.use()

            window.render(current_time, delta)

            window.swap_buffers()

        # confirmed to close window
        logging.info(f"[{cls.__name__}] Confirmed to close window")
        g.mCurrentAppStage = g.AppStage.Close

        _, duration = timer.stop()
        window.destroy()
        logging.info(f"[{cls.__name__}] Window destroyed")
        if duration > 0:
            logging.info(
                "Duration: {0:.2f}s @ {1:.2f} FPS".format(
                    duration, window.frames / duration
                )
            )
        logging.info(f"[{cls.__name__}] End of {cls.__name__}.run()")
