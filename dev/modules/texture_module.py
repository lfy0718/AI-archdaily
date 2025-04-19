import hashlib
import logging
import os.path
import pickle
import time
import uuid
from collections import deque
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import dev
from config import *
from dev.modules import BaseModule
from dev.utils import io_utils, color_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

__runtime__ = True
if not __runtime__:
    from dev.modules.graphic_module import SimpleTexture


class TextureModule(BaseModule):
    _icon_uvs: dict[str: tuple[tuple[float, float]], tuple[float, float]] = {}
    _iconset_tex: "SimpleTexture" = None

    _cached_additional_icons: "dict[str: SimpleTexture]" = {}  # name : simple_texture
    _cached_textures: "dict[str: SimpleTexture]" = {}  # name: simple_texture
    _cached_folder_thumbnails: "dict[str: dict[str: SimpleTexture]]" = {}  # {folder_path: dict[file_name: Texture]}

    @classmethod
    def m_init(cls):
        cls._init_icon_texture_auto()

    @classmethod
    def get_icon_glo(cls, name) -> tuple[int, tuple[float, float], tuple[float, float]]:
        """:return: tex_glo, uv0, uv1"""
        tex, uv0, uv1 = cls.get_icon(name)
        return tex.glo, uv0, uv1

    @classmethod
    def get_icon(cls, name) -> tuple["SimpleTexture", tuple[float, float], tuple[float, float]]:
        """:return: tex, uv0, uv1"""
        if name in cls._icon_uvs:
            # 首先在图表集中查找
            uv0, uv1 = cls._icon_uvs[name]
            return cls._iconset_tex, uv0, uv1
        if name in cls._cached_additional_icons:
            # 若图标集中未找到，则在额外的图标中查找
            return cls._cached_additional_icons[name], (0, 0), (1, 1)
        # 若都没有找到，则用fill图标代替
        uv0, uv1 = cls._icon_uvs["fill"]
        return cls._iconset_tex, uv0, uv1

    @classmethod
    def get_texture_glo(cls, name, suffix='png') -> int:
        return cls.get_texture(name, suffix).glo

    @classmethod
    def get_texture(cls, name, suffix="png") -> "SimpleTexture":
        """直接从本地resources/textures/文件夹中读取纹理"""
        if name in cls._cached_textures:
            return cls._cached_textures[name]
        tex_path = os.path.join(RESOURCES_DIR, f"textures/{name}.{suffix}")
        img = Image.open(tex_path)
        texture = cls.create_texture_from_image(img, f"_texture_{name}")
        cls._cached_textures[name] = texture
        logging.debug(f"Create new texture named {name}, id = {texture.glo}")
        return texture

    @classmethod
    def create_texture_from_image(cls, image: Image, name=None) -> "dev.modules.graphic_module.SimpleTexture":
        # must be called after NE.set_window_event()
        width, height = image.size
        channels = 3 if image.mode == 'RGB' else 4
        data = image.tobytes()
        simple_texture = dev.modules.graphic_module.SimpleTexture(str(uuid.uuid4()) if name is None else name, width, height, channels)
        simple_texture.write(data)
        return simple_texture



    @classmethod
    def get_folder_thumbnails(cls, folder_path, icon_size=64, add_mode=False, force_update=False) -> dict:
        if folder_path in cls._cached_folder_thumbnails and not force_update and not add_mode:
            return cls._cached_folder_thumbnails[folder_path]

        if force_update and folder_path in cls._cached_folder_thumbnails.keys():
            logging.info("Getting Folder Thumbnails: force_update")
            texes = [texture for texture in cls._cached_folder_thumbnails[folder_path].values()]
            for tex in texes:
                tex.release()
            cls._cached_folder_thumbnails[folder_path] = {}
        if folder_path not in cls._cached_folder_thumbnails.keys():
            logging.info("Getting Folder Thumbnails: first init")
            cls._cached_folder_thumbnails[folder_path] = {}

        for file in os.listdir(folder_path):
            if file in cls._cached_folder_thumbnails[folder_path].keys():
                continue

            file_path = os.path.join(folder_path, file)
            file_path = file_path.replace('/', '\\')
            if not os.path.isfile(file_path):
                continue
            tex_info = cls.GalleryTextureInfo(file_path, icon_size)  # 创建代理对象，只有当真正需要图像时才触发加载工作
            cls._cached_folder_thumbnails[folder_path][file] = tex_info

        return cls._cached_folder_thumbnails[folder_path]

    @classmethod
    def get_cached_textures(cls):
        return cls._cached_textures

    @classmethod
    def get_cached_additional_icons(cls):
        return cls._cached_additional_icons

    @classmethod
    def get_cached_folder_thumbnails(cls):
        return cls._cached_folder_thumbnails

    @classmethod
    def clear_cache(cls):
        # clear all cache
        # =======
        for key, tex in cls._cached_additional_icons.items():
            tex.release()
        cls._cached_additional_icons.clear()
        # =======
        for key, tex in cls._cached_textures.items():
            tex.release()
        cls._cached_textures.clear()
        # =======
        for _, value in cls._cached_folder_thumbnails.items():
            for key, tex in value.items():
                tex.release()
        cls._cached_folder_thumbnails.clear()
        # Complete

    @classmethod
    def _init_icon_texture(cls, iconset_name="light", tint_color=(1, 1, 1, 1), force_regenerate=False):
        icon_folder = os.path.join(RESOURCES_DIR, f'icons/{iconset_name}')
        pkl_path = os.path.join(RESOURCES_DIR, f'icons/{iconset_name}.pkl')
        img_path = os.path.join(RESOURCES_DIR, f'icons/{iconset_name}.png')

        tint_color = np.array(tint_color, dtype=np.float32)

        if cls._iconset_tex is not None:
            cls._iconset_tex.release()
        cls._icon_uvs.clear()

        def __load_from_local_file() -> bool:
            """return success or not"""
            if not os.path.exists(pkl_path):
                return False

            with open(pkl_path, "rb") as f:
                data = pickle.load(f)

            image_path = data["image_path"]
            if not os.path.exists(image_path):
                return False
            image = Image.open(image_path)

            # handle tint
            image = image.convert("RGBA")
            image_array = np.array(image, dtype=np.float32) / 255.0
            image_array *= tint_color
            image_array = (image_array * 255.0).astype(np.uint8)
            image = Image.fromarray(image_array)

            cls._icon_uvs = data["uv_ranges"]
            cls._iconset_tex = cls.create_texture_from_image(image, "_IconSet")
            return True

        def __create_new_icon_set() -> bool:
            icons = [name for name in os.listdir(icon_folder) if name.lower().endswith(".png")]
            logger.debug(f"{len(icons)} loaded")
            icon_size = 32
            num_icons = len(icons)
            side_length = int(num_icons ** 0.5)
            if side_length * side_length < num_icons:
                side_length += 1
            canvas_size = side_length * icon_size
            canvas = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
            uv_ranges = {}
            for idx, icon_name in enumerate(icons):
                icon_path = os.path.join(icon_folder, icon_name)
                icon_image = Image.open(icon_path).resize((icon_size, icon_size))
                row = idx // side_length
                col = idx % side_length
                x = col * icon_size
                y = row * icon_size

                canvas.paste(icon_image, (x, y))
                uv_ranges[icon_name.split('.')[0]] = (
                    (x / canvas_size, y / canvas_size),  # uv0
                    ((x + icon_size) / canvas_size, (y + icon_size) / canvas_size)  # uv1
                )
            canvas.save(img_path)
            output_data = {
                "image_path": img_path,
                "uv_ranges": uv_ranges
            }

            with open(pkl_path, "wb") as f:
                pickle.dump(output_data, f)
            return True

        # ===
        # main
        icon_loaded = __load_from_local_file() if not force_regenerate else False
        if icon_loaded: return

        __create_new_icon_set()
        __load_from_local_file()

    @classmethod
    def _init_icon_texture_auto(cls):
        iconset_name = "light"
        tint_color = (1, 1, 1, 1)
        cls._init_icon_texture(iconset_name=iconset_name, tint_color=tint_color)

    @classmethod
    def _on_global_scale_changed(cls):
        cls.clear_cache()

    @classmethod
    def _on_dark_mode_changed(cls):
        cls._init_icon_texture_auto()

    class GalleryTextureInfo:
        TexGetterQueue = deque()

        @classmethod
        def update_gallery_texture_info(cls):
            # 每帧执行
            if len(cls.TexGetterQueue) > 0:
                cls.TexGetterQueue.popleft()()

        def __init__(self, file_path, icon_size):
            self._file_path = file_path
            self._file_name = os.path.basename(self._file_path)
            self._icon_size = icon_size
            self._cached_texture: Optional[dev.modules.graphic_module.SimpleTexture] = None
            self._tex_getter_pushed = False

        def _tex_getter_func(self):
            if not self._tex_getter_pushed:
                # 当执行tex_getter时，_tex_getter_pushed必须是True的状态，否则可以判断该对象已经在执行真正的获取任务前被销毁了。
                return
            file_name = os.path.basename(self._file_path)
            pil_image = io_utils.get_file_thumbnail(self._file_path, self._icon_size)
            self._cached_texture: dev.modules.graphic_module.SimpleTexture = TextureModule.create_texture_from_image(pil_image, f"_thumbnail_{file_name}")

        def _query_texture(self):
            if len(TextureModule.GalleryTextureInfo.TexGetterQueue) > 4:
                return
            logging.info(f"query texture for {self.file_path}")
            TextureModule.GalleryTextureInfo.TexGetterQueue.append(self._tex_getter_func)
            self._tex_getter_pushed = True

        @property
        def file_path(self):
            return self._file_path

        @property
        def file_name(self):
            return self._file_name

        @property
        def texture(self):
            if self._cached_texture is None and not self._tex_getter_pushed:
                self._query_texture()
            if self._cached_texture is None:
                return TextureModule.get_texture("Default_Black")
            else:
                return self._cached_texture

        def has_texture(self):
            return self._cached_texture is not None

        def can_release(self):
            """满足清理机制的轮询需求"""
            curr_time = time.time()
            if self._cached_texture is None and not self._tex_getter_pushed:
                # 当没有加载texture， 并且也没有请求texture
                return True
            if self._cached_texture is not None and (curr_time - self._cached_texture.last_render_time) > 5:
                # 如果已经请求过texture了，并且已经很久没有渲染过了
                return True
            return False

        def release(self):
            if self._cached_texture is not None:
                self._cached_texture.release()
            self._cached_texture = None
            self._tex_getter_pushed = False  # 置为False后，如果有正在执行的任务，遇到False标识符将不进行texture的赋予工作

        @property
        def icon_size(self):
            return self._icon_size

        @icon_size.setter
        def icon_size(self, value):
            value = max(32, value)
            if value != self._icon_size:
                if self._cached_texture is not None:
                    self._cached_texture.release()
                    self._cached_texture = None
            self._icon_size = value
