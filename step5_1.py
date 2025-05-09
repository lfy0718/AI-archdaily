# 本程序将从已有的文件夹中，查找是否存在content.html文件，如果不存在，则爬取页面内容，并保存为content.html文件
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from config import *
from utils.html_utils import request_project_html_archdaily, flush_success_queue
from utils.logging_utils import init_logger

init_logger('step5_1')


def main():
    logging.info(
        "本程序将从已有的文件夹中，查找是否存在content.html文件，如果不存在，则爬取页面内容，并保存为content.html文件")
    logging.info(f"正在扫描本地文件...")

    all_projects = os.listdir(user_settings.archdaily_projects_dir)
    project_id_queue: list[str] = []

    # 遍历项目目录下的所有子文件夹
    for project_id in tqdm(all_projects):
        folder_path = os.path.join(user_settings.archdaily_projects_dir, project_id)
        if os.path.isdir(folder_path):
            html_file_path = os.path.join(folder_path, f'content.html')  # 扫描是否有content.html
            if not os.path.exists(html_file_path):
                project_id_queue.append(project_id)

    logging.info(f"共计{len(all_projects)}个项目，其中{len(project_id_queue)}个项目没有content.html文件，需要爬取")
    if not len(project_id_queue):
        exit(0)

    logging.info("开始爬取页面内容...")
    _invalid_project_ids = set()  # 在这个部分我们不需要用到这个set， 理论上现有的所有文件夹都应该是能够访问的，如果这里面出现了无法访问的文件夹，说明存在问题。

    def _get_html_content(project_id: str, i: int):
        request_project_html_archdaily(project_id, i, len(project_id_queue), _invalid_project_ids, force_update=False)

    # 使用ThreadPoolExecutor进行并发爬取
    with ThreadPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(_get_html_content, project_id, i) for i, project_id in enumerate(project_id_queue)]
        for future in as_completed(futures):
            future.result()
    flush_success_queue('content_html')

    logging.info("爬取完成")

    if _invalid_project_ids:
        logging.warning(f"这些项目为404，请检查原因：{_invalid_project_ids}")


if __name__ == '__main__':
    main()
