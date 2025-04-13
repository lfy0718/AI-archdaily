# step1: 爬取ArchDaily大约500个页面上的json数据，保存至results/pages文件夹中
import json
import os
import random
import time

import requests
import logging
from datetime import datetime
# 配置日志
log_dir = f'./log/step1'
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
from headers import headers

base_url = "https://www.archdaily.com/search/api/v1/us/projects"
pages = list(range(1, 501))

# 检查本地results/projects文件夹中是否已经存在对应的JSON文件
results_dir = 'results/pages'
if not os.path.exists(results_dir):
    os.makedirs(results_dir)

existing_pages = []
for page in pages:
    file_name = f'page_{str(page).zfill(5)}.json'
    file_path = os.path.join(results_dir, file_name)
    if os.path.exists(file_path):
        existing_pages.append(page)

# 从列表中删除已经存在的页码
pages = [page for page in pages if page not in existing_pages]

# 爬取每个页码的数据并保存为JSON文件
for page in pages:
    url = f'{base_url}?page={page}'
    response = requests.get(url, headers=headers, timeout=20)
    if response.status_code == 200:
        data = response.json()
        file_name = f'page_{str(page).zfill(5)}.json'
        file_path = os.path.join(results_dir, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logging.info(f'Saved {file_name}')
    else:
        logging.error(f'Failed to fetch page {page}, url={url}, code={response.status_code}')
