# 根据content.json文件中的信息，爬取ImageGallery相关图片并保存，支持并发下载
import json
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from datetime import datetime

import requests
from tqdm import tqdm

# 配置日志
log_dir = f'./log/step6'
os.makedirs(log_dir, exist_ok=True)
log_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.log'
log_file_path = os.path.join(log_dir, log_filename)

# 创建一个文件处理器，设置编码为UTF-8
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter("%(levelname)-8s %(asctime)-24s %(filename)-24s:%(lineno)-4d | %(message)s"))

# 创建一个控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter("%(levelname)-8s %(asctime)-24s %(filename)-24s:%(lineno)-4d | %(message)s"))

# 获取根日志器，并添加处理器
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 定义项目目录
projects_dir = './results/projects'
image_size_type = 'large'  # 可选项：large, slideshow, medium

logging.info(f"正在扫描本地文件...")
json_path_queue = []
content_not_exist_count = 0
all_projects = os.listdir(projects_dir)

# 遍历项目目录下的所有子文件夹
for folder_name in tqdm(all_projects):
    folder_path = os.path.join(projects_dir, folder_name)
    if not os.path.isdir(folder_path):
        continue
    json_file_path = os.path.join(folder_path, 'content.json')
    if not os.path.exists(json_file_path):
        content_not_exist_count += 1  # content.json does not exist, add to content_not_exist_count
        continue
    image_gallery_folder = os.path.join(folder_path, 'image_gallery', image_size_type)
    # image_gallery_folder example: ./results/projects/<project_id>/image_gallery/<image_size_type>
    if not os.path.exists(image_gallery_folder):
        json_path_queue.append(json_file_path)  # image_gallery_folder does not exist, add to json_path_queue
        continue
    image_gallery_names = os.listdir(image_gallery_folder)
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    image_gallery_images = data.get('image_gallery', [])
    if len(image_gallery_names) < len(image_gallery_images):
        json_path_queue.append(json_file_path)

logging.info(
    f"已扫描{len(all_projects)}个项目，其中{content_not_exist_count}个项目没有content.json文件，{len(json_path_queue)}个项目需要下载图像")
logging.info("开始下载图像...")


def download_image(json_file_path, i):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    folder_path = os.path.dirname(json_file_path)
    project_id = os.path.basename(folder_path)

    image_gallery_images = data.get('image_gallery', [])
    for img_index, image_gallery_image in enumerate(image_gallery_images):
        try:
            img_path = os.path.join(folder_path, 'image_gallery', image_size_type, f'{str(img_index).zfill(5)}.jpg')
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            img_url = image_gallery_image.get(f'url_{image_size_type}')
            if not img_url:
                logging.warning(f'[{i}/{len(json_path_queue)}] No url_{image_size_type} found for project {project_id}')

            response = requests.get(img_url)
            if response.status_code == 200:
                with open(img_path, 'wb') as img_file:
                    img_file.write(response.content)
                logging.info(
                    f'[{i}/{len(json_path_queue)}][{img_index}/{len(image_gallery_images)}] success for project {project_id}')
            else:
                logging.warning(f'[{i}/{len(json_path_queue)}][{img_index}/{len(image_gallery_images)}] Failed to '
                                f'download image for project {project_id}, code {response.status_code}')

        except Exception as e:
            logging.error(
                f'[{i}/{len(json_path_queue)}][{img_index}/{len(image_gallery_images)}] project {project_id} error: {str(e)}')
        time.sleep(random.random() * 0.2)


# 使用ThreadPoolExecutor进行并发下载
with ThreadPoolExecutor(max_workers=32) as executor:
    futures: list[Future] = [executor.submit(download_image, json_file_path, i) for i, json_file_path in enumerate(json_path_queue)]
    for future in as_completed(futures):
        future.result()
