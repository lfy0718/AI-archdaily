import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from config import *
from utils.html_utils import parse_project_content_archdaily, flush_success_queue, ArchdailyFlags
from utils.logging_utils import init_logger

init_logger('step5_3')


def main():
    logging.info(f"本程序将扫描所有项目的content.html， 并将其内容增量解析到content.json")
    logging.info(f"正在扫描本地文件...")
    project_id_queue = []
    all_projects = os.listdir(user_settings.archdaily_projects_dir)
    for project_id in all_projects:
        html_file_path = os.path.join(user_settings.archdaily_projects_dir, project_id, 'content.html')
        if os.path.exists(html_file_path):
            project_id_queue.append(project_id)
    if len(all_projects) - len(project_id_queue) > 0:
        logging.warning(f"{len(all_projects) - len(project_id_queue)}个项目没有content.html文件，请运行前置代码补充")

    logging.info(f"共计{len(all_projects)}个项目，其中{len(project_id_queue)}个项目需要检查")
    def _parse_project_content(project_id: str, i: int):
        time.sleep(0.02)
        parse_project_content_archdaily(project_id, i, len(all_projects),
                                        flags=ArchdailyFlags.NONE)

    with ThreadPoolExecutor(max_workers=64) as executor:
        futures = []
        logging.info("正在将任务添加到队列...")
        for i, project_id in tqdm(enumerate(project_id_queue), total=len(project_id_queue)):
            futures.append(executor.submit(_parse_project_content, project_id, i))
        logging.info("开始解析页面内容... 如果遇到image_gallery为空的情况，可能需要等待返回image_gallery结果")
        for future in tqdm(as_completed(futures), total=len(futures)):
            future.result()
    flush_success_queue('content_json')
    logging.info('complete')


if __name__ == '__main__':
    main()
