import json
import logging
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from headers import headers

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

base_url = "https://www.archdaily.com/"
# 需要忽略的关键词列表
ignore_keywords = {
    "Projects", "Images", "Products", "Folders", "AD Plus",
    "Benefits", "Archive", "Content", "Maps", "Audio",
    "Check the latest Chairs", "Check the latest Counters"
}
# 定义项目目录
projects_dir = './results/projects'

# 全局变量，存储所有项目
all_projects = os.listdir(projects_dir)


def extract_project_content(project_id: str, i: int):
    try:
        output_data = {'main_content': [], 'image_gallery': []}  # list of dict, list of dict
        # 请求指定的HTML文件
        url = f"{base_url}{project_id}"
        response = requests.get(url, headers=headers)
        html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')
        paragraphs = soup.find_all(['p', 'figure'])  # 同时提取<p>和<figure>标签
        seen = set()  # 用于记录已经出现过的内容
        main_content = []  # 用于按顺序存储正文内容

        for element in paragraphs:
            if element.name == 'p':
                # 提取<p>标签中的文本，忽略<a>标签
                text = element.get_text().strip()  # 去除前后空白字符
                if text and len(text) >= 20 and text not in seen and text not in ignore_keywords:  # 如果内容非空且长度大于等于20且未出现过且不在忽略列表中
                    seen.add(text)  # 记录到seen中
                    text_info = {'type': 'text', 'content': text}
                    main_content.append(text_info)  # 按顺序添加到list中
            elif element.name == 'figure':
                # 提取<figure>标签中的<img>标签的alt和src属性
                img = element.find('img')
                if img and img.get('alt') and img.get('src'):
                    alt_text = img.get('alt').strip()
                    src = img.get('src').strip()
                    if alt_text and src:
                        image_info = {'type': 'image', 'alt': alt_text, 'src': src}
                        main_content.append(image_info)
        output_data['main_content'] = main_content

        # 额外爬取image gallery
        gallery_thumbs = soup.find('ul', class_='gallery-thumbs')
        if gallery_thumbs:
            gallery_thumbs_link = gallery_thumbs.find('a', class_='gallery-thumbs-link')
            if gallery_thumbs_link and gallery_thumbs_link.get('href'):
                gallery_url = gallery_thumbs_link['href']
                if gallery_url.startswith("/"):
                    gallery_url = base_url + gallery_url[1:]
                gallery_response = requests.get(gallery_url, headers=headers)
                gallery_html_content = gallery_response.text
                gallery_soup = BeautifulSoup(gallery_html_content, 'html.parser')
                output_data['image_gallery'] = extract_project_gallery(project_id, gallery_soup)
        json_file_path = os.path.join(projects_dir, project_id, "content.json")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

        if len(output_data['main_content']) == 0:
            logging.warning(f"[{i + 1}/{len(all_projects)}] project: {project_id} no main_content")
        if len(output_data['image_gallery']) == 0:
            logging.warning(f"[{i + 1}/{len(all_projects)}] project: {project_id} no image_gallery")
        logging.info(f"[{i + 1}/{len(all_projects)}] project: {project_id} success")

    except Exception as e:
        logging.error(f'[{i + 1}/{len(all_projects)}] project {project_id} error: {str(e)}')
def extract_project_gallery(project_id, gallery_soup) -> list[dict]:
    output = []
    try:
        gallery_items = gallery_soup.find('div', id='gallery-items', class_='afd-gal-items')
        if gallery_items and gallery_items.get('data-images'):
            text = gallery_items['data-images']
            text = text.replace('&quot;', '"')  # 替换 &quot; 为双引号
            text_data: list[dict] = json.loads(text)
            for line in text_data:
                if 'url_large' in line:
                    output.append(line)
    except Exception as e:
        logging.error(f'project {project_id} 解析gallery时发生错误, error: {str(e)}')
    return output


def main():
    logging.info(f"正在扫描本地文件...")
    project_id_queue: list[str] = []

    # 遍历项目目录下的所有子文件夹
    for folder_name in tqdm(all_projects):
        folder_path = os.path.join(projects_dir, folder_name)
        if os.path.isdir(folder_path):
            json_file_path = os.path.join(folder_path, f'content.json')  # 扫描是否有content.json文件
            if not os.path.exists(json_file_path):
                project_id_queue.append(folder_name)

    logging.info(f"共计{len(all_projects)}个项目，其中{len(project_id_queue)}个项目需要爬取")
    logging.info("开始爬取页面内容...")

    # 使用ThreadPoolExecutor进行并发爬取
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(extract_project_content, project_id, i) for i, project_id in enumerate(project_id_queue)]
        for future in as_completed(futures):
            future.result()


if __name__ == '__main__':
    main()
