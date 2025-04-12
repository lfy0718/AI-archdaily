import json
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from tqdm import tqdm

# 配置日志
log_dir = f'./log/{__name__}'
os.makedirs(log_dir, exist_ok=True)
log_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.log'
log_file_path = os.path.join(log_dir, log_filename)

# 创建一个文件处理器，设置编码为UTF-8
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(levelname)-8s %(asctime)-24s %(filename)-24s:%(lineno)-4d | %(message)s"))

# 创建一个控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(levelname)-8s %(asctime)-24s %(filename)-24s:%(lineno)-4d | %(message)s"))

# 获取根日志器，并添加处理器
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 定义项目目录
projects_dir = './results/projects'
image_size_type = 'large'  # 可选项：large, medium, small, thumb, newsletter, slideshow, mini, small_portrait

logging.info(f"正在扫描本地文件...")
json_path_queue = []
all_projects = os.listdir(projects_dir)

# 遍历项目目录下的所有子文件夹
for folder_name in tqdm(all_projects):
    folder_path = os.path.join(projects_dir, folder_name)
    if os.path.isdir(folder_path):
        # 检查是否存在{image_size_type}.jpg文件
        img_path = os.path.join(folder_path, f'{image_size_type}.jpg')
        if not os.path.exists(img_path):
            # 打开对应的JSON文件
            json_file_path = os.path.join(folder_path, f'{folder_name}.json')
            json_path_queue.append(json_file_path)

logging.info(f"共计{len(all_projects)}个项目，其中{len(json_path_queue)}个项目需要下载图像")


def download_image(json_file_path, i):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    folder_path = os.path.dirname(json_file_path)
    project_id = os.path.basename(folder_path)
    img_path = os.path.join(folder_path, f'{image_size_type}.jpg')
    featured_images = data.get('featured_images', [])
    if featured_images:
        try:
            img_url = featured_images.get(f'url_{image_size_type}')
            if img_url:
                response = requests.get(img_url)
                if response.status_code == 200:
                    with open(img_path, 'wb') as img_file:
                        img_file.write(response.content)
                    logging.info(f'[{i}/{len(json_path_queue)}] Downloaded {image_size_type}.jpg for project {project_id}')
                else:
                    logging.warning(f'[{i}/{len(json_path_queue)}] Failed to download image for project {project_id}')
            else:
                logging.warning(f'[{i}/{len(json_path_queue)}] No url_{image_size_type} found for project {project_id}')
        except Exception as e:
            logging.error(f'[{i}/{len(json_path_queue)}] project {project_id} error: {str(e)}')
        time.sleep(random.random())
    else:
        logging.warning(f'[{i}/{len(json_path_queue)}] No featured_images found for {project_id}')


# 使用ThreadPoolExecutor进行并发下载
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(download_image, json_file_path, i) for i, json_file_path in enumerate(json_path_queue)]
    for future in as_completed(futures):
        future.result()
