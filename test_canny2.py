# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/28/2025 11:03 AM
# @Function:
import datetime
import math
import os
import random
from abc import abstractmethod

import PIL.Image
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from matplotlib import pyplot as plt
from tqdm import tqdm


class EmbeddingImageProcessor:
    def __init__(self, name):
        self.name = name
    @abstractmethod
    def apply(self, image: Image.Image):
        pass


class CannyImageProcessor(EmbeddingImageProcessor):
    def __init__(self, name, resolution: int = 512):
        super().__init__(name)
        self.resolution = resolution

    def apply(self, image: Image.Image):
        # 预处理：缩放到 256x256
        image.thumbnail((256, 256), Image.Resampling.NEAREST)
        img_rgb = np.array(image.convert("RGB"))

        # 颜色量化（8x8x8=512种颜色）
        quantized = (img_rgb // 32) * 32

        # 预分配8x8x8计数数组（代替np.unique）
        color_cube = np.zeros((8, 8, 8), dtype=np.int32)
        # 将量化后的颜色映射到三维索引
        indices = quantized // 32
        np.add.at(color_cube, (indices[..., 0], indices[..., 1], indices[..., 2]), 1)

        # 提取非零颜色和数量
        nonzero_mask = color_cube > 0
        counts = color_cube[nonzero_mask]
        color_indices = np.stack(np.where(nonzero_mask), axis=1)
        # 将索引转回实际颜色值
        colors = color_indices * 32

        # 计算明度抑制（矢量化计算）
        R, G, B = colors[:, 0], colors[:, 1], colors[:, 2]
        L = (0.299 * R + 0.587 * G + 0.114 * B) / 255
        suppress_factor = 0.5 + 0.5 * L
        suppressed_counts = counts * suppress_factor

        # 计算统计指标
        total = suppressed_counts.sum()
        max_count = suppressed_counts.max()
        max_percent = max_count / total
        probs = suppressed_counts / total
        entropy = -np.sum(probs * np.log(probs + 1e-10)) / math.log(len(probs))
        entropy = math.pow(entropy, 0.5)
        score = (max_percent * 2 + (1.0 - entropy) * 1) / 3.0

        # 可视化部分保持不变
        result_img = Image.fromarray(quantized)
        draw = ImageDraw.Draw(result_img)
        info_text = (
            f"Max Color: {max_percent:.2f}\n"
            f"~Entropy: {(1 - entropy):.2f}\n"
            f"Score: {score: .2f}"
        )
        draw.rectangle([(10, 10), (100, 60)], fill=(0, 0, 0, 50))
        draw.text((15, 15), info_text, fill=(255, 255, 255), spacing=4)

        is_planar = score > 0.5
        return result_img, is_planar, max_percent, entropy

num_image = 100
projects = os.listdir("./results/archdaily/projects")
print(len(projects))
random.seed(1000)
random.shuffle(projects)
project_cursor = -1
image_paths = []
while len(image_paths) < num_image:
    project_cursor += 1
    if project_cursor >= len(projects):
        print("reached end")
        break
    project = projects[project_cursor]
    image_folder = os.path.join("./results/archdaily/projects", project, "image_gallery/large")
    if not os.path.isdir(image_folder):
        continue
    image_names = os.listdir(image_folder)
    _image_paths = [os.path.join(image_folder, image_name) for image_name in image_names]
    image_paths.extend(_image_paths)

image_paths = image_paths[:num_image]
print(len(image_paths))

image_processor = CannyImageProcessor("canny_512", resolution=512)

outputs = []
for i, image_path in tqdm(enumerate(image_paths), total=len(image_paths), desc="Loading and Processing"):
    image = Image.open(image_path)
    result_img, is_planar, max_percent, entropy = image_processor.apply(image)
    outputs.append((result_img, is_planar, max_percent, entropy))

save_folder = f"./tmp/{image_processor.name}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
os.makedirs(save_folder, exist_ok=True)
os.makedirs(os.path.join(save_folder, "is_planar"), exist_ok=True)
os.makedirs(os.path.join(save_folder, "is_photo"), exist_ok=True)
for i, (result_img, is_planar, max_percent, entropy) in tqdm(enumerate(outputs), total=len(outputs), desc="Saving Images"):
    folder = os.path.join(save_folder, "is_planar" if is_planar else "is_photo")
    result_img.save(os.path.join(folder, f"{str(i).zfill(5)}.jpg"))
print(f"images saved to {save_folder}")


# 生成散点图
plt.figure(figsize=(10, 6))
for result_img, is_planar, max_percent, entropy in outputs:
    color = 'red' if is_planar else 'blue'
    plt.scatter(max_percent, entropy, c=color, alpha=0.6)

plt.xlabel("Max Color Percentage (%)")
plt.ylabel("Color Entropy")
plt.title("Image Classification: Planar (Red) vs. Photo (Blue)")
plt.grid(True)

# 保存散点图
scatter_path = os.path.join(save_folder, "scatter_plot.png")
plt.savefig(scatter_path, dpi=300, bbox_inches='tight')
plt.close()