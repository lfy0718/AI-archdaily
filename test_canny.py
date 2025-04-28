# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/28/2025 11:03 AM
# @Function:
import datetime
import os
import random
from abc import abstractmethod

import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm


class EmbeddingImageProcessor:
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def apply(self, image: Image.Image) -> Image.Image | list[Image.Image]:
        pass


class CannyImageProcessor(EmbeddingImageProcessor):
    def __init__(self, name, resolution: int = 512):
        super().__init__(name)
        self.resolution = resolution

    def apply(self, image: Image.Image):
        image.thumbnail((self.resolution, self.resolution))
        image = image.convert("RGB")
        image = np.array(image)
        image = cv2.Canny(image, 100, 200)
        image = cv2.bitwise_not(image)
        image = image[:, :, None]
        image = np.concatenate([image, image, image], axis=2)
        image = Image.fromarray(image)
        return image

num_image = 100
projects = os.listdir("./results/archdaily/projects")
random.seed(42)
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
    image_paths = [os.path.join(image_folder, image_name) for image_name in image_names]
    image_paths.extend(image_paths)

image_paths = image_paths[:num_image]
print(len(image_paths))

image_processor = CannyImageProcessor("canny_512", resolution=512)

outputs = []
for i, image_path in tqdm(enumerate(image_paths), total=len(image_paths), desc="Loading and Processing"):
    image = Image.open(image_path)
    image = image_processor.apply(image)
    outputs.append(image)

save_folder = f"./tmp/{image_processor.name}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
os.makedirs(save_folder, exist_ok=True)
for i, image in tqdm(enumerate(outputs), total=len(outputs), desc="Saving Images"):
    image.save(os.path.join(save_folder, f"{str(i).zfill(5)}.jpg"))
print(f"images saved to {save_folder}")