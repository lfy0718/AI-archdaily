import json
import os
import random
import time

import requests

from headers import headers

base_url = "https://www.archdaily.com/search/api/v1/us/projects"
# 生成1到500的列表
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
#
# # 打乱列表顺序，减少反爬检测
# random.shuffle(pages)

# 定义模拟正常访问的header


# 爬取每个页码的数据并保存为JSON文件
for page in pages:
    url = f'{base_url}?page={page}'  # 替换为实际的API URL
    response = requests.get(url, headers=headers, timeout=20)
    if response.status_code == 200:
        data = response.json()
        file_name = f'page_{str(page).zfill(5)}.json'
        file_path = os.path.join(results_dir, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f'Saved {file_name}')
    else:
        print(f'Failed to fetch page {page}, url={url}, code={response.status_code}')
    time.sleep(random.uniform(1, 2))  # 随机休眠1到3秒
