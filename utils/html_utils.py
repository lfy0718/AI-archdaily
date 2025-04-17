import json
import logging
import os
import traceback

import requests
from bs4 import BeautifulSoup

from config import *

_success_queues: dict[str: list] = {'content_html': [], 'content_json': []}
_flush_threshold = 64

from enum import IntFlag, auto

class Flags(IntFlag):
    NONE = 0
    FORCE_UPDATE_MAIN_CONTENT = auto()  # 0x0001
    FORCE_UPDATE_IMAGE_GALLERY = auto()  # 0x0010
    FORCE_UPDATE_TITLE = auto()  # 0x0100
    FORCE_UPDATE_TAGS = auto()  # 0x1000

def _add_to_success_queue(queue_name: str, project_id: str):
    queue = _success_queues[queue_name]
    if _flush_threshold > 0:
        queue.append(project_id)
    if len(queue) >= _flush_threshold:
        logging.info(f"project: {','.join(queue)} success")
        queue.clear()


def flush_success_queue(queue_name: str):
    queue = _success_queues[queue_name]
    if len(queue):
        logging.info(f"project: {','.join(queue)} success")
        queue.clear()


def request_project_html(project_id: str, i: int, total: int, invalid_project_ids: set[str],
                         force_update: bool = False):
    """
    请求project的id并保存到本地
    :param force_update: 强制重新爬取
    :param project_id:
    :param i:
    :param total:
    :param invalid_project_ids:
    :return:
    """
    url = f"{base_url}{project_id}"
    html_file_path = os.path.join(projects_dir, project_id, "content.html")
    if os.path.isfile(html_file_path) and not force_update:
        return
    if project_id in invalid_project_ids:
        return
    try:
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code == 404:
            invalid_project_ids.add(project_id)
            return
        if response.status_code != 200:
            logging.error(f"[{i + 1}/{total}] project: {project_id} 请求出现意外情况，状态码: {response.status_code}。")
            return
        html_content: str = response.text
        os.makedirs(os.path.dirname(html_file_path), exist_ok=True)
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        _add_to_success_queue('content_html', project_id)
    except Exception as e:
        logging.error(f"[{i + 1}/{total}] project: {project_id} 请求出现意外情况, error: {str(e)}")


def parse_project_content(project_id: str, i: int, total: int, flags: Flags = Flags.NONE):

    html_file_path = os.path.join(projects_dir, project_id, "content.html")
    json_file_path = os.path.join(projects_dir, project_id, "content.json")
    if not os.path.isfile(html_file_path):
        logging.warning(f"[{i + 1}/{total}] project: {project_id} html文件不存在, 请先获取html文件")
        return
    soup = None
    def get_soup():
        """延迟get"""
        nonlocal soup
        if soup is not None:
            return soup

        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup

    try:
        output_data = {}
        if os.path.isfile(json_file_path):
            with open(json_file_path, 'r', encoding='utf-8') as f:
                try:
                    output_data = json.load(f)
                except Exception as e:
                    logging.error(f'[{i + 1}/{total}] project {project_id} json文件读取失败 error: {str(e)}')
        any_change = False

        # 爬取main content
        if 'main_content' not in output_data or \
                len(output_data['main_content']) == 0 or \
                flags & Flags.FORCE_UPDATE_MAIN_CONTENT:
            success, main_content = extract_main_content(project_id, get_soup())
            if success:
                output_data['main_content'] = main_content
                any_change |= True

        # 爬取image gallery
        if 'image_gallery' not in output_data or \
                flags & Flags.FORCE_UPDATE_IMAGE_GALLERY:
            success, image_gallery = extract_image_gallery(project_id, get_soup())
            if success:
                output_data['image_gallery'] = image_gallery
                any_change |= True
        # 爬取title
        if 'title' not in output_data or \
                flags & Flags.FORCE_UPDATE_TITLE:
            success, title = extract_title(project_id, get_soup())
            if success:
                output_data['title'] = title
                any_change |= True
        # 爬取tags
        if 'tags' not in output_data or \
                flags & Flags.FORCE_UPDATE_TAGS:
            success, tags = extract_tags(project_id, get_soup())
            if success:
                output_data['tags'] = tags
                any_change |= True
        try:
            if any_change:
                os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
                with open(json_file_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=4)
                _add_to_success_queue('content_json', project_id)
        except Exception as e:
            logging.error(f'[{i + 1}/{total}] project {project_id} 保存文件时发生错误 error: {str(e)}')
            traceback.print_exc()
            exit(1)
    except Exception as e:
        logging.error(f'[{i + 1}/{total}] project {project_id} error: {str(e)}')


def extract_main_content(project_id: str, soup) -> tuple[bool, list[dict]]:
    try:
        main_content = []  # 用于按顺序存储正文内容
        seen = set()  # 用于记录已经出现过的内容
        article = soup.find('article')  # 找到<article>标签
        if not article:
            logging.warning(f"[{project_id}] project: {project_id} 没有找到<article>标签")
            return False, []
        paragraphs = article.find_all(['p', 'figure'])  # 在<article>标签内提取<p>和<figure>标签
        for element in paragraphs:
            if element.name == 'p':
                # 提取<p>标签中的文本，忽略<a>标签
                text = element.get_text().strip()  # 去除前后空白字符
                if (not text) or (text in seen) or (text in ignore_keywords) or (len(text) <= 10):
                    continue
                # 如果内容非空且长度大于等于20且未出现过且不在忽略列表中
                seen.add(text)  # 记录到seen中
                text_info = {'type': 'text', 'content': text}  # <-------------------------------------类型1
                main_content.append(text_info)  # 按顺序添加到list中
            elif element.name == 'figure':
                # 提取<figure>标签中的<img>标签的alt和src属性
                img = element.find('img')
                if img and img.get('alt') and img.get('src'):
                    alt_text = img.get('alt').strip()
                    src = img.get('src').strip()
                    if src:
                        image_info = {'type': 'image', 'alt': alt_text, 'src': src}  # <----------------类型2
                        main_content.append(image_info)
        return True, main_content
    except Exception as e:
        logging.error(f'project {project_id} 解析main_content时发生错误, error: {str(e)}')
        return False, []


def extract_image_gallery(project_id, soup) -> tuple[bool, list[dict]]:
    try:
        image_gallery = []
        gallery_thumbs = soup.find('ul', class_='gallery-thumbs')
        if not gallery_thumbs:
            return True, []
        gallery_thumbs_link = gallery_thumbs.find('a', class_='gallery-thumbs-link')
        if not gallery_thumbs_link:
            return True, []
        gallery_url = gallery_thumbs_link['href']
        if gallery_url.startswith("/"):
            gallery_url = base_url + gallery_url[1:]
        gallery_response = requests.get(gallery_url, headers=headers)
        gallery_html_content = gallery_response.text
        gallery_soup = BeautifulSoup(gallery_html_content, 'html.parser')
        gallery_items = gallery_soup.find('div', id='gallery-items', class_='afd-gal-items')
        if gallery_items and gallery_items.get('data-images'):
            data_images: str = gallery_items['data-images']
            data_images: str = data_images.replace('&quot;', '"')  # 替换 &quot; 为双引号
            data_images: list[dict] = json.loads(data_images)
            for data_image in data_images:
                if 'url_large' in data_image:
                    image_gallery.append(data_image)
        return True, image_gallery
    except Exception as e:
        logging.error(f'project {project_id} 解析gallery时发生错误, error: {str(e)}')
    return False, []


def extract_title(project_id: str, soup) -> tuple[bool, str]:
    try:
        headers = soup.find_all('header', class_='article-header')
        if not headers:
            logging.warning(f"[{project_id}] project: {project_id} 没有找到<header>标签")
            return False, ""
        h1 = None
        for header in headers:
            h1 = header.find('h1')
            if h1:
                break
        if not h1:
            logging.warning(f"[{project_id}] project: {project_id} 没有找到h1标签")
            return False, ""
        return True, h1.get_text().strip()
    except Exception as e:
        logging.error(f'project {project_id} 解析header时发生错误, error: {str(e)}')
        return False, ""


def extract_tags(project_id: str, soup) -> tuple[bool, list[str]]:
    try:
        tags = []
        tags_container = soup.find('div', class_='afd-tags__container')
        if not tags_container:
            logging.warning(f"[{project_id}] project: {project_id} 没有找到afd-tags__container标签")
            return False, tags
        tag_buttons = tags_container.find_all('a', class_='afd-tags__btn')
        if not tag_buttons:
            logging.warning(f"[{project_id}] project: {project_id} 没有找到afd-tags__btn标签")
            return False, tags
        for button in tag_buttons:
            tag_text = button.get_text().strip()
            if tag_text:
                tags.append(tag_text)
        return True, tags
    except Exception as e:
        logging.error(f'project {project_id} 解析tags时发生错误, error: {str(e)}')
        return False, []

