import enum
import inspect
import logging
import types
from typing import Optional, Callable, Union, Generator

import imgui

from config import *


class GlobalAppState:
    class AppStage(enum.Enum):
        Prepare = 0
        MainLoop = 1
        Close = 2

        Update = 10
        RenderUI = 11
        LateUpdate = 12

        Undefined = -1

    def __init__(self):
        # [WINDOW EVENTS]
        self.mTime = 0
        self.mFrametime = 1e-5
        self.mFirstLoop = True
        self.mWindowEvent = None

        self.mIsClosing = False
        self.mConfirmClose = False

        # [FONTS]
        self.mFont = None
        self.mFontL = None
        self.mFontXL = None
        self.mFontXXL = None
        self.mFontBold = None

        # init in style module
        self.mImguiStyle: Optional[imgui.core.GuiStyle] = None

        # io utils
        self.mLastFileDir = r'c://'

        self.mShiftDown = False
        self.mCtrlDown = False

        self.mTmpTexture = None  # 临时预览的图片
        self.mCurrentAppStage = GlobalAppState.AppStage.Undefined

        self.mAliveWorkers = 0
        self.mAliveProjects = []
        self.mProjectStartTimes = {}
        self.mProjectSubTotal = {}
        self.mProjectSubCurr = {}

        self.mSuccessProjects = []
        self._global_scale = user_settings.global_scale  # 重启后生效

        self._mMongoClient = None
        atexit.register(self._at_exit)

    def _at_exit(self):
        if self._mMongoClient is not None:
            self._mMongoClient.close()
            logging.info("MongoDB client closed")

    @property
    def mMongoClient(self):
        return self._mMongoClient

    @mMongoClient.setter
    def mMongoClient(self, value):
        if value is None and self._mMongoClient is not None:
            self._mMongoClient.close()
        self._mMongoClient = value

    @property
    def global_scale(self):
        return self._global_scale

    @property
    def font_size(self):
        return 16 * self.global_scale

    def g_update(self):
        _ = self
        Coroutine.update_coroutines()

    def g_render(self):
        _ = self
        Coroutine.update_coroutines_in_render_loop()

        # imgui.end()

    def g_late_update(self):
        pass

    # region Coroutine related
    @staticmethod
    def run_coroutine(func: Union[types.MethodType, types.FunctionType, type(Generator)], *args,
                      flag_run_in_render_loop=False, **kwargs) -> "Coroutine":
        if isinstance(func, types.MethodType):
            __self__ = func.__self__
            func = func.__func__
            args = (__self__,) + args
        assert isinstance(func, types.FunctionType), "func must be type of FunctionType"
        # 获取函数的代码对象
        code = func.__code__
        has_yield = bool(code.co_flags & inspect.CO_GENERATOR)
        if not has_yield:
            raise Exception(f"no yield found in {func.__name__}")
        generator = func(*args, **kwargs)
        coroutine = Coroutine(generator, flag_run_in_render_loop=flag_run_in_render_loop)
        return coroutine

    @staticmethod
    def stop_coroutine(coroutine: "Coroutine"):
        Coroutine.stop_coroutine(coroutine)

    @staticmethod
    def is_coroutine_running(coroutine: "Coroutine"):
        return Coroutine.is_coroutine_running(coroutine)

    @staticmethod
    def NewWaitForSeconds(seconds: float) -> "WaitForSeconds":
        return WaitForSeconds(seconds)

    @staticmethod
    def NewWaitUntil(func: Callable[[], bool]) -> "WaitUntil":
        return WaitUntil(func)
    # endregion


class Coroutine:
    coroutines: set["Coroutine"] = set()
    coroutines_to_add: set["Coroutine"] = set()
    coroutines_to_remove: set["Coroutine"] = set()

    coroutines_to_execute_in_render_loop: set["Coroutine"] = set()

    def __init__(self, generator, flag_run_in_render_loop=False):
        self.generator = generator
        self.conditions: list["CoroutineCondition"] = []
        self.is_complete = False
        self.flag_run_in_render_loop = flag_run_in_render_loop
        Coroutine.coroutines_to_add.add(self)

    def co_update(self):
        # check conditions
        while len(self.conditions) > 0:
            condition = self.conditions[0]
            if not condition.check():
                return
            self.conditions.pop(0)

        try:
            output = next(self.generator)
            if isinstance(output, CoroutineCondition):
                self.conditions.append(output)

        except StopIteration:
            Coroutine.coroutines_to_remove.add(self)
            self.is_complete = True
            return

    @staticmethod
    def update_coroutines():

        for coroutine in Coroutine.coroutines_to_add:
            Coroutine.coroutines.add(coroutine)
        Coroutine.coroutines_to_add.clear()
        for coroutine in Coroutine.coroutines_to_remove:
            Coroutine.coroutines.remove(coroutine)
        Coroutine.coroutines_to_remove.clear()

        for coroutine in Coroutine.coroutines:
            if not coroutine.flag_run_in_render_loop:
                coroutine.co_update()
            else:
                Coroutine.coroutines_to_execute_in_render_loop.add(coroutine)

    @staticmethod
    def update_coroutines_in_render_loop():
        for coroutine in Coroutine.coroutines_to_execute_in_render_loop:
            coroutine.co_update()
        Coroutine.coroutines_to_execute_in_render_loop.clear()

    @staticmethod
    def stop_coroutine(coroutine: "Coroutine"):
        if coroutine is None:
            return
        coroutine.is_complete = True
        if coroutine in Coroutine.coroutines:
            Coroutine.coroutines_to_remove.add(coroutine)

    @staticmethod
    def is_coroutine_running(coroutine: "Coroutine"):
        return coroutine in Coroutine.coroutines and not coroutine.is_complete


class CoroutineCondition:
    pass

    def check(self) -> bool:
        raise NotImplemented


class WaitForSeconds(CoroutineCondition):
    def __init__(self, seconds):
        self.start_time = g.mTime
        self.end_time = g.mTime + seconds

    def check(self):
        if g.mTime > self.end_time:
            return True
        return False


class WaitUntil(CoroutineCondition):
    def __init__(self, func: Callable[[], bool]):
        self.func = func

    def check(self):
        return self.func()


g = GlobalAppState()
