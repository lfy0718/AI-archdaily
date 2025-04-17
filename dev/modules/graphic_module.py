import time
from abc import abstractmethod

import moderngl
import numpy as np

from dev.global_app_state import g
from dev.modules import BaseModule


class GraphicModule(BaseModule):
    registered_simple_textures: list["SimpleTexture"] = []
    registered_frame_buffer_textures: list["FrameBufferTexture"] = []

    @classmethod
    def m_init(cls):
        pass

    @classmethod
    def register_simple_texture(cls, texture: "SimpleTexture"):
        cls.registered_simple_textures.append(texture)

    @classmethod
    def unregister_simple_texture(cls, texture: "SimpleTexture"):
        cls.registered_simple_textures.remove(texture)

    @classmethod
    def register_fbt(cls, fbt: "FrameBufferTexture"):
        cls.registered_frame_buffer_textures.append(fbt)

    @classmethod
    def unregister_fbt(cls, fbt: "FrameBufferTexture"):
        cls.registered_frame_buffer_textures.remove(fbt)


class SimpleTexture(moderngl.Texture):
    def __init__(self, name, width, height, channel, dtype="f1"):
        self.name = name
        self.ctx: moderngl.Context = g.mWindowEvent.ctx

        self.texture: moderngl.Texture = self.ctx.texture((width, height), channel, dtype=dtype)
        g.mWindowEvent.imgui.register_texture(self.texture)
        GraphicModule.register_simple_texture(self)

        # init super
        self.mglo = self.texture.mglo
        self._size = self.texture.size
        self._components = self.texture.components
        self._samples = self.texture.samples
        self._dtype = self.texture.dtype
        self._depth = self.texture.depth
        self._glo = self.texture.glo
        self.extra = self.texture.extra

        self.last_render_time = -1  # Note: we use time.time() here instead of g.mTime to record the last render time

    def release(self):
        if self not in GraphicModule.registered_simple_textures:
            return
        self.texture.release()
        g.mWindowEvent.imgui.remove_texture(self.texture)
        GraphicModule.unregister_simple_texture(self)

    @property
    def glo(self):
        self.last_render_time = time.time()
        return self._glo

    def write(
            self,
            data,
            viewport=None,
            level=0,
            alignment=1,
    ):
        super().write(data, viewport, level, alignment)
        self.last_render_time = time.time()

    def read(self, level=0, alignment=1):
        super().read(level, alignment)
        self.last_render_time = time.time()

    def read_into(
            self,
            buffer,
            level=0,
            alignment=1,
            write_offset=0,
    ):
        super().read_into(buffer, level, alignment, write_offset)
        self.last_render_time = time.time()


class FrameBufferTexture:
    """
    使用modernGL 的 FrameBuffer作为渲染画布的高级Texture对象
    此类为基类， 实现了基础属性的获取与修改，支持改变texture的尺寸并自动注册和销毁
    要对该Texture进行修改，需要继承该类并对render方法进行修改
    """

    def __init__(self, name, width, height, channel=4, with_depth=True, samples=0):
        self.name = name
        self.width, self.height, self.channel = width, height, channel
        self.with_depth = with_depth
        self.samples = samples

        self.ctx: moderngl.Context = g.mWindowEvent.ctx
        self.wnd = g.mWindowEvent.wnd

        self.last_render_time = -1  # Note: we use time.time() here instead of g.mTime to record the last render time

        # 新建一个frame buffer object， 在上面进行渲染绘图
        self._fbo = self.ctx.framebuffer(
            color_attachments=self.ctx.texture(size=(width, height), components=channel, samples=samples),
            depth_attachment=self.ctx.depth_texture(size=(width, height),
                                                    samples=samples) if with_depth else None)  # frame buffer object
        g.mWindowEvent.imgui.register_texture(self.fbo.color_attachments[0])
        if with_depth:
            g.mWindowEvent.imgui.register_texture(self.fbo.depth_attachment)
        GraphicModule.register_fbt(self)

    def release(self):
        if self not in GraphicModule.registered_frame_buffer_textures:
            return
        g.mWindowEvent.imgui.remove_texture(self.fbo.color_attachments[0])
        self.fbo.color_attachments[0].release()  # manually release

        if self.with_depth:
            g.mWindowEvent.imgui.remove_texture(self.fbo.depth_attachment)
            self.fbo.depth_attachment.release()
        GraphicModule.unregister_fbt(self)

    @property
    def texture(self):
        return self.fbo.color_attachments[0]

    @property
    def texture_id(self):
        return self.texture.glo

    @property
    def fbo(self):
        # self.last_render_time = time.time()
        return self._fbo

    # @fbo.setter
    # def fbo(self, value):
    #     self._fbo = value

    def update_size(self, width, height):
        if width == self.width and height == self.height:
            return

        g.mWindowEvent.imgui.remove_texture(self.fbo.color_attachments[0])
        self.fbo.color_attachments[0].release()  # manually release

        if self.with_depth:
            g.mWindowEvent.imgui.remove_texture(self.fbo.depth_attachment)
            self.fbo.depth_attachment.release()

        self.width, self.height = width, height

        self._fbo = self.ctx.framebuffer(
            color_attachments=self.ctx.texture(size=(width, height), components=self.channel, samples=self.samples),
            depth_attachment=self.ctx.depth_texture(size=(width, height),
                                                    samples=self.samples) if self.with_depth else None)

        g.mWindowEvent.imgui.register_texture(self.fbo.color_attachments[0])
        if self.with_depth:
            g.mWindowEvent.imgui.register_texture(self.fbo.depth_attachment)

    @abstractmethod
    def render(self, **kwargs):
        raise NotImplementedError

    def frame_to_arr(self) -> np.ndarray:
        """output shape: Height, Width, Channel"""
        buffer = self.texture.read()
        img_arr = np.frombuffer(buffer, dtype=np.uint8).reshape(
            (self.height, self.width, self.channel))
        return img_arr
