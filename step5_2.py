# Step5-2： 暴力根据project id 爬取。爬取项目的页面内容及Image Gallery信息，保存为content.json， 分为两个list， {'main_content': [], 'image_gallery': []}， 支持并发下载
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from config import *
from utils.html_utils import request_project_html_archdaily, flush_success_queue
from utils.logging_utils import init_logger

init_logger('step5_2')

# 从本地文件加载invalid_project_ids
invalid_project_ids_path = './results/invalid_project_ids.json'
if os.path.exists(invalid_project_ids_path):
    with open(invalid_project_ids_path, 'r', encoding='utf-8') as f:
        invalid_project_ids = set(json.load(f))
else:
    invalid_project_ids = set()

complete = False


def save_invalid_project_ids():
    with open(user_settings.archdaily_invalid_projects_ids_path, 'w', encoding='utf-8') as f:
        logging.info("保存invalid_project_ids")
        json.dump(list(invalid_project_ids), f, ensure_ascii=False, indent=4)


# 新增定时保存的函数
def timer_save_invalid_project_ids():
    while not complete:
        time.sleep(60)
        save_invalid_project_ids()


def main():
    global complete
    # 获取用户输入的开始和结束project id序号
    start_id = int(input("请输入开始的project id序号: "))
    end_id = int(input("请输入结束的project id序号: "))

    # 转换为str列表
    id_range = list(range(start_id, end_id + 1)) if start_id <= end_id else list(range(end_id, start_id + 1))
    if start_id > end_id:
        id_range.reverse()
    project_id_queue_full: list[str] = [str(project_id) for project_id in id_range]
    # 扣除all_projects已经存在的项目
    all_projects_set = set(os.listdir(user_settings.archdaily_projects_dir))
    project_id_queue = [project_id for project_id in project_id_queue_full if project_id not in all_projects_set]
    # 扣除invalid_project_ids
    project_id_queue = [project_id for project_id in project_id_queue if project_id not in invalid_project_ids]
    # logging.info(project_id_queue)
    print(f"共计{len(project_id_queue_full)}个项目，其中{len(project_id_queue)}个项目需要爬取")
    if not input("开始？[y/n]") == 'y':
        exit(0)
    logging.info("开始爬取页面内容...")

    # 启动定时保存任务
    threading.Thread(target=timer_save_invalid_project_ids).start()

    def _request_project_html(project_id: str, i: int):
        request_project_html_archdaily(project_id, i, len(project_id_queue), invalid_project_ids, force_update=False)

    # 使用ThreadPoolExecutor进行并发爬取
    with ThreadPoolExecutor(max_workers=64) as executor:
        futures = [executor.submit(_request_project_html, project_id, i) for i, project_id in
                   enumerate(project_id_queue)]
        for future in tqdm(as_completed(futures), total=len(futures)):
            future.result()
    complete = False
    flush_success_queue('content_html')
    logging.info("complete")
    save_invalid_project_ids()


if __name__ == '__main__':
    main()
