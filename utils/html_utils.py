import logging
import random
import time
import traceback
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import *

_success_queues: dict[str: list] = {'content_html': [], 'content_json': []}
_flush_threshold = 64

from enum import IntFlag, auto


class ArchdailyFlags(IntFlag):
    NONE = 0
    FORCE_UPDATE_MAIN_CONTENT = auto()  # 0x00000001
    FORCE_UPDATE_IMAGE_GALLERY = auto()  # 0x00000010
    FORCE_UPDATE_TITLE = auto()  # 0x00000100
    FORCE_UPDATE_TAGS = auto()  # 0x00001000
    FORCE_UPDATE_SPECS = auto()  # 0x00010000


class GoooodFlags(IntFlag):
    NONE = 0
    FORCE_UPDATE_MAIN_CONTENT = auto()  # 0x00000001
    FORCE_UPDATE_IMAGE_GALLERY = auto()  # 0x00000010
    FORCE_UPDATE_TITLE = auto()  # 0x00000100
    FORCE_UPDATE_TAGS = auto()  # 0x00001000
    FORCE_UPDATE_SPECS = auto()  # 0x00010000


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


def request_project_html_archdaily(project_id: str, i: int, total: int, invalid_project_ids: set[str],
                                   force_update: bool = False) -> Optional[bool]:
    """
    请求project的id并保存到本地
    :param force_update: 强制重新爬取
    :param project_id:
    :param i:
    :param total:
    :param invalid_project_ids:
    :return: None代表无错误完成， False代表错误， True代表成功
    """
    url = f"{user_settings.archdaily_base_url}{project_id}"
    html_file_path = os.path.join(user_settings.archdaily_projects_dir, project_id, "content.html")
    if os.path.isfile(html_file_path) and not force_update:
        return None
    if project_id in invalid_project_ids:
        return None
    try:
        response = requests.get(url, headers=user_settings.headers, timeout=60)
        if response.status_code == 404:
            invalid_project_ids.add(project_id)
            return None
        if response.status_code != 200:
            logging.error(f"[{i + 1}/{total}] project: {project_id} 请求出现意外情况，状态码: {response.status_code}。")
            return False
        html_content: str = response.text
        os.makedirs(os.path.dirname(html_file_path), exist_ok=True)
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        _add_to_success_queue('content_html', project_id)
        return True
    except Exception as e:
        logging.error(f"[{i + 1}/{total}] project: {project_id} 请求出现意外情况, error: {str(e)}")
        return False


def parse_project_content_archdaily(project_id: str, i: int, total: int, flags: ArchdailyFlags = ArchdailyFlags.NONE) -> Optional[bool]:
    """返回True表示改变， False表示错误， None表示无变化"""
    html_file_path = os.path.join(user_settings.archdaily_projects_dir, project_id, "content.html")
    json_file_path = os.path.join(user_settings.archdaily_projects_dir, project_id, "content.json")
    if not os.path.isfile(html_file_path):
        logging.warning(f"[{i + 1}/{total}] project: {project_id} html文件不存在, 请先获取html文件")
        return False
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
                flags & ArchdailyFlags.FORCE_UPDATE_MAIN_CONTENT:
            success, main_content = extract_main_content_archdaily(project_id, get_soup())
            if success:
                output_data['main_content'] = main_content
                any_change |= True

        # 爬取image gallery
        if 'image_gallery' not in output_data or \
                flags & ArchdailyFlags.FORCE_UPDATE_IMAGE_GALLERY:
            success, image_gallery = extract_image_gallery_archdaily(project_id, get_soup())
            if success:
                output_data['image_gallery'] = image_gallery
                any_change |= True
        # 爬取title
        if 'title' not in output_data or \
                flags & ArchdailyFlags.FORCE_UPDATE_TITLE:
            success, title = extract_title_archdaily(project_id, get_soup())
            if success:
                output_data['title'] = title
                any_change |= True
        # 爬取year
        if 'specs' not in output_data or \
                flags & ArchdailyFlags.FORCE_UPDATE_SPECS:
            if 'year' in output_data:
                output_data.pop('year')  # 删除之前由于旧数据格式问题，保留year字段
            success, specs = extract_specs_archdaily(project_id, get_soup())
            if success:
                output_data['specs'] = specs
                any_change |= True
        # 爬取tags
        if 'tags' not in output_data or \
                flags & ArchdailyFlags.FORCE_UPDATE_TAGS:
            success, tags = extract_tags_archdaily(project_id, get_soup())
            if success:
                output_data['tags'] = tags
                any_change |= True

        if any_change:
            os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
            _add_to_success_queue('content_json', project_id)
            return True
        else:
            return None
    except Exception as e:
        logging.error(f'[{i + 1}/{total}] project {project_id} error: {str(e)}')
        return False


def extract_main_content_archdaily(project_id: str, soup) -> tuple[bool, list[dict]]:
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
                if (not text) or (text in seen) or (text in user_settings.archdaily_ignore_keywords) or (len(text) <= 10):
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


def extract_image_gallery_archdaily(project_id, soup) -> tuple[bool, list[dict]]:
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
            gallery_url = user_settings.archdaily_base_url + gallery_url[1:]
        gallery_response = requests.get(gallery_url, headers=user_settings.headers)
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


def extract_title_archdaily(project_id: str, soup) -> tuple[bool, str]:
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


def extract_tags_archdaily(project_id: str, soup) -> tuple[bool, list[str]]:
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


def extract_specs_archdaily(project_id: str, soup) -> tuple[bool, dict]:
    # all keys should in lowercase
    result = {'year': None,
              'country': None,
              'city': None,
              'area': None,
              'architects': None,
              'photographs': None}
    try:
        specs_items = soup.find_all('li', class_='afd-specs__item')
        for item in specs_items:
            key_span = item.find('span', class_='afd-specs__key')
            value_span = item.find('span', class_='afd-specs__value')
            if not key_span or not value_span:
                continue
            key: str = key_span.get_text().strip().lower()  # use lowercase
            value: str = value_span.get_text().strip()
            for query_key in result.keys():
                if query_key in key:
                    result[query_key] = value

        return True, result
    except Exception as e:
        logging.error(f'project {project_id} 解析时发生错误, error: {str(e)}')
        return False, result


def download_images_archdaily(project_id, i, total, image_size_type="large", img_index_change_callback=None) -> Optional[bool]:
    return download_images_common(user_settings.archdaily_projects_dir, project_id, i, total, image_size_type, img_index_change_callback)


def parse_project_content_gooood(project_id: str, i: int, total: int, flags: GoooodFlags = GoooodFlags.NONE) -> Optional[bool]:
    """返回True表示改变， False表示错误， None表示无变化"""
    data_file_path = os.path.join(user_settings.gooood_projects_dir, project_id, f"{project_id}.json")
    json_file_path = os.path.join(user_settings.gooood_projects_dir, project_id, "content.json")
    if not os.path.isfile(data_file_path):
        logging.warning(f"[{i + 1}/{total}] {project_id}.json文件不存在, 请先获取json文件")
        return False
    soup = None

    with open(data_file_path, 'r', encoding='utf-8') as f:
        project_data = json.load(f)

    def get_soup():
        """延迟get"""
        nonlocal soup
        if soup is not None:
            return soup
        html_content = project_data['content']['rendered']
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
                flags & GoooodFlags.FORCE_UPDATE_MAIN_CONTENT:
            success, main_content = extract_main_content_gooood(project_id, get_soup())
            if success:
                output_data['main_content'] = main_content
                any_change |= True

        # 爬取image gallery
        if 'image_gallery' not in output_data or \
                flags & GoooodFlags.FORCE_UPDATE_IMAGE_GALLERY:
            success, image_gallery = extract_image_gallery_gooood(project_id, project_data)
            if success:
                output_data['image_gallery'] = image_gallery
                any_change |= True
        # 爬取title
        if 'title' not in output_data or \
                flags & GoooodFlags.FORCE_UPDATE_TITLE:
            success, title = extract_title_gooood(project_id, project_data)
            if success:
                output_data['title'] = title
                any_change |= True
        # 爬取year
        if 'specs' not in output_data or \
                flags & GoooodFlags.FORCE_UPDATE_SPECS:
            if 'year' in output_data:
                output_data.pop('year')  # 删除之前由于旧数据格式问题，保留year字段
            success, specs = extract_specs_gooood(project_id, project_data)
            if success:
                output_data['specs'] = specs
                any_change |= True
        # 爬取tags
        if 'tags' not in output_data or \
                flags & GoooodFlags.FORCE_UPDATE_TAGS:
            success, tags = extract_tags_gooood(project_id, project_data)
            if success:
                output_data['tags'] = tags
                any_change |= True

        if any_change:
            os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
            _add_to_success_queue('content_json', project_id)
            return True
        else:
            return None
    except Exception as e:
        logging.error(f'[{i + 1}/{total}] project {project_id} error: {str(e)}')
        return False


def extract_main_content_gooood(project_id: str, soup) -> tuple[bool, list[dict]]:
    try:
        main_content = []  # 用于按顺序存储正文内容
        for element in soup.find_all(['p', 'img']):
            if element.name == 'p':
                # 移除span标签后检查是否为纯文本
                temp_p = element
                for span in temp_p.find_all('span'):
                    span.decompose()
                if temp_p.get_text(strip=True) and not temp_p.find_all():
                    main_content.append({'type': "text", 'content': element.get_text(strip=True)})
            elif element.name == 'img':
                # 保存img元素的所有属性
                attr_data = dict(element.attrs)
                src = attr_data.get('data-src', "").replace("\"", "")
                alt = attr_data.get('alt', "").replace("\"", "")
                img_data = {'type': "image", 'alt': alt, 'src': src}
                main_content.append(img_data)
        if len(main_content) == 0:
            logging.warning(f'project {project_id} main_content为空, 请注意')

        # 处理图片注释
        for i in range(len(main_content) - 1):
            if main_content[i]['type'] == 'text' and main_content[i]['content'].startswith("▼") and main_content[i + 1]['type'] == 'image':
                main_content[i + 1]['alt'] = main_content[i]['content'].replace("▼", "")
                main_content[i]['type'] = "delete"
        main_content = [item for item in main_content if item['type'] != "delete"]  # 删除图片注释文本
        return True, main_content
    except Exception as e:
        error_traceback = traceback.format_exc()
        logging.error(f'project {project_id} 解析main_content时发生错误, error: {str(e)}\nTraceback:\n{error_traceback}')
        return False, []


def extract_image_gallery_gooood(project_id, project_data: dict) -> tuple[bool, list[dict]]:
    try:
        image_gallery = []
        for img_data in project_data['gallery']:
            if 'full_url' in img_data:
                image_gallery.append({'url_large': img_data['full_url']})
        return True, image_gallery
    except Exception as e:
        logging.error(f'project {project_id} 解析gallery时发生错误, error: {str(e)}')
    return False, []


def extract_title_gooood(project_id: str, project_data: dict) -> tuple[bool, str]:
    try:
        return True, project_data['title']['fulltitle']
    except Exception as e:
        logging.error(f'project {project_id} 解析header时发生错误, error: {str(e)}')
        return False, ""


def extract_tags_gooood(project_id: str, project_data: dict) -> tuple[bool, list[str]]:
    try:
        tags = []
        tags_data = project_data['taxonomies']['post_tag']
        if not tags_data:  # false or []
            return True, []
        for tab_data in tags_data:
            tags.append(tab_data['name'])
        return True, tags
    except Exception as e:
        logging.error(f'project {project_id} 解析tags时发生错误, error: {str(e)}')
        return False, []


def extract_specs_gooood(project_id: str, project_data: dict) -> tuple[bool, dict]:
    # all keys should in lowercase
    result = {'year': None,
              'country': None,
              'city': None,
              'area': None,
              'architects': None,
              'photographs': None}
    try:
        if 'date' in project_data:
            dt = datetime.strptime(project_data['date'], "%Y-%m-%dT%H:%M:%S")
            result['year'] = str(dt.year)
        if 'taxonomies' in project_data:
            taxonomies = project_data['taxonomies']
            if 'country' in taxonomies:
                if isinstance(taxonomies['country'], list):
                    result['country'] = taxonomies['country'][0]['name']
                elif isinstance(taxonomies['country'], bool):
                    pass
                else:
                    logging.warning(f'project {project_id} country ({type(taxonomies["country"])})is not list, this is not expected, please check your code')
            if 'office' in taxonomies:
                if isinstance(taxonomies['office'], list):
                    result['architects'] = taxonomies['office'][0]['name']
                elif isinstance(taxonomies['office'], bool):
                    pass
                else:
                    logging.warning(f'project {project_id} office ({type(taxonomies["office"])}) is not list, this is not expected, please check your code')

        return True, result
    except Exception as e:
        logging.error(f'project {project_id} 解析时发生错误, error: {str(e)}')
        return False, result


def download_images_gooood(project_id, i, total, image_size_type="large", img_index_change_callback=None) -> Optional[bool]:
    return download_images_common(user_settings.gooood_projects_dir, project_id, i, total, image_size_type, img_index_change_callback)


def download_images_common(projects_dir, project_id, i, total, image_size_type="large", img_index_change_callback=None):
    folder_path = os.path.join(projects_dir, project_id)
    json_file_path = os.path.join(projects_dir, project_id, "content.json")
    if not os.path.isfile(json_file_path):
        logging.error(f'[{i}/{total}] project {project_id} content.json not exist')
        return False
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f'[{i}/{total}] project {project_id} cannot load json, error: {str(e)}')
        return False

    image_gallery_images = data.get('image_gallery', [])
    for img_index, image_gallery_image in enumerate(image_gallery_images):
        try:
            if img_index_change_callback:
                img_index_change_callback(project_id, img_index, len(image_gallery_images))
            img_path = os.path.join(folder_path, 'image_gallery', image_size_type, f'{str(img_index).zfill(5)}.jpg')
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            if os.path.isfile(img_path):
                # logging.info(f'[{i}/{total}][{img_index}/{len(image_gallery_images)}] image_gallery image exist for project {project_id}')
                continue
            img_url = image_gallery_image.get(f'url_{image_size_type}')
            if not img_url:
                logging.warning(f'[{i}/{total}] No url_{image_size_type} found for project {project_id}')

            response = requests.get(img_url, timeout=60)
            if response.status_code == 200:
                with open(img_path, 'wb') as img_file:
                    img_file.write(response.content)
                logging.info(
                    f'[{i}/{total}][{img_index}/{len(image_gallery_images)}] success for project {project_id}')
            else:
                logging.warning(f'[{i}/{total}][{img_index}/{len(image_gallery_images)}] Failed to '
                                f'download image for project {project_id}, code {response.status_code}')

        except Exception as e:
            logging.error(
                f'[{i}/{total}][{img_index}/{len(image_gallery_images)}] project {project_id} error: {str(e)}')
        time.sleep(random.random() * 0.2)
    return True