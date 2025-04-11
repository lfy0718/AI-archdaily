# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/11/2025 9:32 PM
# @Function:

import json
import os
import random
import time

import requests
base_url = "https://www.archdaily.com/search/api/v1/us/projects"
# 生成1到500的列表
pages = list(range(1, 501))

# 检查本地results/projects文件夹中是否已经存在对应的JSON文件
results_dir = 'results/projects'
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
headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "max-age=0",
    "Host": "www.archdaily.com",
    "Priority": "u=0, i",
    "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "\"Windows\"",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
}

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