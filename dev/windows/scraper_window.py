# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 3/28/2025 10:47 AM
# @Function:
import json
import logging
import os
import threading
import time
from concurrent.futures import Future

import imgui
from tqdm import tqdm

from config import *
from dev.components import c
from dev.global_app_state import g
from dev.windows.base_window import PopupWindow
from utils.html_utils import Flags


class ScraperWindow(PopupWindow):
    @classmethod
    def w_init(cls):
        super().w_init()
        cls.w_open()

    @classmethod
    def w_update(cls):
        super().w_update()

    @classmethod
    def w_open(cls):
        super().w_open()

    @classmethod
    def w_close(cls):
        super().w_close()

    @classmethod
    def w_before_window_begin(cls):
        pass

    @classmethod
    def w_after_window_end(cls):
        pass

    _all_projects = []
    _projects_id_queue_for_scraping_html = []
    _projects_id_queue_for_parsing_html = []
    _projects_id_queue_for_downloading_image = []
    _project_id_start = "1000000"
    _project_id_end = "1000100"
    _is_working = False
    _stop_working = False
    _working_context = None
    _num_workers = 32
    _image_size_type = "large"
    _start_after_scan = False

    _scanning_total = 1
    _scanning_curr = 0
    _working_total = 1
    _working_curr = 0

    @classmethod
    def w_content(cls):
        super().w_content()

        with imgui.font(g.mFontL):
            c.ctext("AI-Archdaily Scraper Tool")
        if imgui.begin_tab_bar("steps"):
            if imgui.begin_tab_item("Step1-下载html").selected:
                if cls._working_context is not None and not cls._working_context.startswith("Step1"):
                    c.info_box("step_error", f"当前正在执行{cls._working_context}任务", "warning")
                else:
                    cls.step1()
                imgui.end_tab_item()
            if imgui.begin_tab_item("Step2-解析html").selected:
                if cls._working_context is not None and not cls._working_context.startswith("Step2"):
                    c.info_box("step_error", f"当前正在执行{cls._working_context}任务", "warning")
                else:
                    cls.step2()
                imgui.end_tab_item()
            if imgui.begin_tab_item("Step3-下载图像").selected:
                if cls._working_context is not None and not cls._working_context.startswith("Step3"):
                    c.info_box("step_error", f"当前正在执行{cls._working_context}任务", "warning")
                else:
                    cls.step3()
                imgui.end_tab_item()
            imgui.end_tab_bar()

    @classmethod
    def step1(cls):
        imgui.text("步骤1： 下载项目html页面到本地")
        c.gray_text("原来的step5-1和5-2")
        c.gray_text("文件将保存为content.html")
        if imgui.begin_tab_bar("get_project_id_queue"):
            if imgui.begin_tab_item("方案1： 从现有的文件夹扫描").selected:
                c.begin_child_auto_height("scrapper_html_method1", bg_color=(0, 0, 0, 0.2))
                c.gray_text("此方案将扫描现有的项目文件夹中是否存在content.html， 如果没有则补充")
                if cls._working_context != "Step1-scan1":
                    if c.button("扫描需要下载的项目id(方案1)",
                                disabled=cls._is_working,
                                width=imgui.get_content_region_available_width()):
                        cls.scan_projects_folder()
                else:
                    if c.dangerous_button("取消扫描", width=imgui.get_content_region_available_width()):
                        cls._stop_working = True

                if cls._is_working:
                    c.gray_text(f"当前进度: {cls._scanning_curr} / {cls._scanning_total}")
                    imgui.progress_bar(cls._scanning_curr / cls._scanning_total,
                                       (imgui.get_content_region_available_width(), 10 * g.global_scale))
                c.end_child_auto_height("scrapper_html_method1")
                imgui.end_tab_item()
            if imgui.begin_tab_item("方案2： 手动指定项目id范围").selected:
                c.begin_child_auto_height("scrapper_html_method2", bg_color=(0, 0, 0, 0.2))
                c.gray_text("此方案将下载指定范围内的项目html页面到本地")

                _, cls._project_id_start = c.input_text("start id", cls._project_id_start)
                _, cls._project_id_end = c.input_text("end id", cls._project_id_end)
                if cls._working_context != "Step1-scan2":
                    if c.button("扫描需要下载的项目id(方案2)",
                                disabled=cls._is_working,
                                width=imgui.get_content_region_available_width()):
                        cls.get_valid_project_ids()
                else:
                    if c.dangerous_button("取消扫描", width=imgui.get_content_region_available_width()):
                        cls._stop_working = True
                if cls._is_working:
                    c.gray_text(f"当前进度: {cls._scanning_curr} / {cls._scanning_total}")
                    imgui.progress_bar(cls._scanning_curr / cls._scanning_total,
                                       (imgui.get_content_region_available_width(), 10 * g.global_scale))
                c.end_child_auto_height("scrapper_html_method2")
                imgui.end_tab_item()
            imgui.end_tab_bar()
        _, cls._start_after_scan = imgui.checkbox("扫描完成后自动开始任务", cls._start_after_scan)
        imgui.text("扫描结果")
        project_id_queue_count = len(cls._projects_id_queue_for_scraping_html)
        imgui.text(f"当前有{project_id_queue_count}个项目没有html文件")
        if project_id_queue_count == 0:
            c.info_box("no_project_id_queue_for_html_scrapping", "没有需要下载html的项目", "info")
            return

        if cls._working_context != "Step1-download":
            if c.highlighted_button("下载项目html页面到本地",
                                    disabled=cls._is_working,
                                    width=imgui.get_content_region_available_width()):
                cls.download_projects_html_to_local()
        else:
            if not cls._stop_working:
                if c.dangerous_button("取消下载", width=imgui.get_content_region_available_width()):
                    cls._stop_working = True
            else:
                if c.dangerous_button("取消下载（请等待现有任务完成）", width=imgui.get_content_region_available_width(),
                                      disabled=True):
                    pass
        if cls._is_working:
            c.gray_text(f"当前下载进度: {cls._working_curr} / {cls._working_total}")
            imgui.progress_bar(cls._working_curr / cls._working_total,
                               (imgui.get_content_region_available_width(), 10 * g.global_scale))

    @classmethod
    def step2(cls):
        imgui.text("步骤2： 解析content.html")
        c.gray_text("原来的step5-3")
        c.gray_text("文件将保存为content.json")

        c.begin_child_auto_height("parse_html", bg_color=(0, 0, 0, 0.2))
        c.gray_text("扫描现有的项目文件夹中是否存在content.html")
        if cls._working_context != "Step2-scan":
            if c.button("扫描项目中的content.html",
                        disabled=cls._is_working,
                        width=imgui.get_content_region_available_width()):
                cls.scan_projects_folder_for_parsing_content()
        else:
            if c.dangerous_button("取消扫描"):
                cls._stop_working = True

        if cls._is_working:
            c.gray_text(f"当前进度: {cls._scanning_curr} / {cls._scanning_total}")
            imgui.progress_bar(cls._scanning_curr / cls._scanning_total,
                               (imgui.get_content_region_available_width(), 10 * g.global_scale))
        c.end_child_auto_height("parse_html")
        _, cls._start_after_scan = imgui.checkbox("扫描完成后自动开始任务", cls._start_after_scan)
        imgui.text("扫描结果")
        project_id_queue_count = len(cls._projects_id_queue_for_parsing_html)
        imgui.text(f"待解析项目队列长度：{project_id_queue_count}")
        if len(cls._all_projects) > 0 and len(cls._projects_id_queue_for_parsing_html) > 0:
            no_html_file_count = len(cls._all_projects) - len(cls._projects_id_queue_for_parsing_html)
            if no_html_file_count:
                c.info_box("no_html_warning", f"有{no_html_file_count}个项目没有content.html，请注意")
            else:
                c.info_box("healthy_project", "所有的项目都有content.html, 你的项目很健康~", "success")
        if project_id_queue_count == 0:
            c.info_box("no_project_id_queue_for_html_parsing", "没有需要解析html项目", "info")
            return

        if cls._working_context != "Step2-parse":
            if c.highlighted_button("开始解析html",
                                    disabled=cls._is_working,
                                    width=imgui.get_content_region_available_width()):
                cls.parse_htmls()
        else:
            if not cls._stop_working:
                if c.dangerous_button("取消解析", width=imgui.get_content_region_available_width()):
                    cls._stop_working = True
            else:
                if c.dangerous_button("取消解析（请等待现有任务完成）", width=imgui.get_content_region_available_width(),
                                      disabled=True):
                    pass
        if cls._is_working:
            c.gray_text(f"当前进度: {cls._working_curr} / {cls._working_total}")
            imgui.progress_bar(cls._working_curr / cls._working_total,
                               (imgui.get_content_region_available_width(), 10 * g.global_scale))

    @classmethod
    def step3(cls):
        imgui.text("步骤3： 下载图片")
        c.gray_text("原来的step6")

        c.begin_child_auto_height("download image", bg_color=(0, 0, 0, 0.2))
        c.gray_text("扫描现有的项目文件夹中的image gallery是否和content.json中的数量匹配")
        if cls._working_context != "Step3-scan":
            if c.button("扫描项目图像文件",
                        disabled=cls._is_working,
                        width=imgui.get_content_region_available_width()):
                cls.scan_projects_folder_for_downloading_images()

        else:
            if c.dangerous_button("取消扫描"):
                cls._stop_working = True

        if cls._is_working:
            c.gray_text(f"当前进度: {cls._scanning_curr} / {cls._scanning_total}")
            imgui.progress_bar(cls._scanning_curr / cls._scanning_total,
                               (imgui.get_content_region_available_width(), 10 * g.global_scale))
        c.end_child_auto_height("download image")
        _, cls._start_after_scan = imgui.checkbox("扫描完成后自动开始任务", cls._start_after_scan)
        imgui.text("扫描结果")
        project_id_queue_count = len(cls._projects_id_queue_for_downloading_image)
        imgui.text(f"待下载的项目队列长度：{project_id_queue_count}")
        if project_id_queue_count == 0:
            c.info_box("no_project_id_queue_for_downloading_image", "没有需要下载图像的项目", "info")
            return

        if cls._working_context != "Step3-download":
            if c.highlighted_button("开始下载",
                                    disabled=cls._is_working,
                                    width=imgui.get_content_region_available_width()):
                cls.download_gallery_images()
        else:
            if not cls._stop_working:
                if c.dangerous_button("取消下载", width=imgui.get_content_region_available_width()):
                    cls._stop_working = True
            else:
                if c.dangerous_button("取消下载（请等待现有任务完成）", width=imgui.get_content_region_available_width(),
                                      disabled=True):
                    pass
        if cls._is_working:
            c.gray_text(f"当前进度: {cls._working_curr} / {cls._working_total}")
            imgui.progress_bar(cls._working_curr / cls._working_total,
                               (imgui.get_content_region_available_width(), 10 * g.global_scale))

    @classmethod
    def scan_projects_folder(cls):
        if cls._is_working:
            logging.warning("其他任务正在进行...")
            return

        def _scan_projects_folder():
            cls._is_working = True
            cls._working_context = "Step1-scan1"
            cls._stop_working = False
            cls._all_projects = os.listdir(projects_dir)
            cls._scanning_total = len(cls._all_projects)
            if cls._scanning_total == 0:
                logging.warning("项目文件夹为空")
                cls._scanning_total = 1  # 不要让其为0
                return

            cls._scanning_curr = 0
            cls._projects_id_queue_for_scraping_html.clear()
            # 遍历项目目录下的所有子文件夹
            for project_id in cls._all_projects:
                if cls._stop_working:
                    break
                cls._scanning_curr += 1
                folder_path = os.path.join(projects_dir, project_id)
                if os.path.isdir(folder_path):
                    html_file_path = os.path.join(folder_path, f'content.html')  # 扫描是否有content.html
                    if not os.path.exists(html_file_path):
                        cls._projects_id_queue_for_scraping_html.append(project_id)
            cls._is_working = False
            cls._working_context = None

            if cls._start_after_scan:
                cls.download_projects_html_to_local()

        threading.Thread(target=_scan_projects_folder).start()

    @classmethod
    def get_valid_project_ids(cls):
        if cls._is_working:
            logging.warning("其他任务正在进行...")
            return

        def _get_valid_project_ids():
            cls._is_working = True
            cls._working_context = "Step1-scan2"
            cls._scanning_curr = 0
            cls._scanning_total = 4
            start_id = int(cls._project_id_start)
            end_id = int(cls._project_id_end)
            # 从本地文件加载invalid_project_ids
            if os.path.exists(invalid_project_ids_path):
                with open(invalid_project_ids_path, 'r', encoding='utf-8') as f:
                    invalid_project_ids = set(json.load(f))
            else:
                invalid_project_ids = set()
            cls._scanning_curr = 1
            id_range = list(range(start_id, end_id + 1)) if start_id <= end_id else list(range(end_id, start_id + 1))
            if start_id > end_id:
                id_range.reverse()
            project_id_queue_full: list[str] = [str(project_id) for project_id in id_range]
            cls._scanning_curr = 2
            # 扣除all_projects已经存在的项目
            all_projects_set = set(os.listdir(projects_dir))
            project_id_queue = [project_id for project_id in project_id_queue_full if
                                project_id not in all_projects_set]
            cls._scanning_curr = 3
            # 扣除invalid_project_ids
            project_id_queue = [project_id for project_id in project_id_queue if
                                project_id not in invalid_project_ids]
            cls._scanning_curr = 4
            cls._projects_id_queue_for_scraping_html = project_id_queue
            cls._is_working = False
            cls._working_context = None

            if cls._start_after_scan:
                cls.download_projects_html_to_local()

        threading.Thread(target=_get_valid_project_ids).start()

    @classmethod
    def scan_projects_folder_for_parsing_content(cls):
        if cls._is_working:
            logging.warning("其他任务正在进行...")
            return

        def _scan_projects_folder():
            cls._is_working = True
            cls._working_context = "Step2-scan"
            cls._stop_working = False
            cls._all_projects = os.listdir(projects_dir)
            cls._scanning_total = len(cls._all_projects)
            if cls._scanning_total == 0:
                logging.warning("项目文件夹为空")
                cls._scanning_total = 1  # 不要让其为0
                return

            cls._scanning_curr = 0
            logging.info(f"本程序将扫描所有项目的content.html， 并将其内容增量解析到content.json")
            logging.info(f"正在扫描本地文件...")
            cls._projects_id_queue_for_parsing_html.clear()
            for project_id in cls._all_projects:
                if cls._stop_working:
                    break
                html_file_path = os.path.join(projects_dir, project_id, 'content.html')
                if os.path.exists(html_file_path):
                    cls._projects_id_queue_for_parsing_html.append(project_id)
                cls._scanning_curr += 1
            if len(cls._all_projects) - len(
                    cls._projects_id_queue_for_parsing_html) > 0 and not cls._stop_working:
                logging.warning(
                    f"{len(cls._all_projects) - len(cls._projects_id_queue_for_parsing_html)}个项目没有content.html文件，请运行前置代码补充")

            logging.info(
                f"共计{len(cls._all_projects)}个项目，其中{len(cls._projects_id_queue_for_parsing_html)}个项目需要检查")

            cls._is_working = False
            cls._working_context = None

            if cls._start_after_scan:
                cls.parse_htmls()

        threading.Thread(target=_scan_projects_folder).start()

    @classmethod
    def scan_projects_folder_for_downloading_images(cls):
        if cls._is_working:
            logging.warning("其他任务正在进行...")
            return

        def _scan_projects_folder():
            cls._is_working = True
            cls._working_context = "Step3-scan"
            cls._stop_working = False
            cls._all_projects = os.listdir(projects_dir)
            cls._scanning_total = len(cls._all_projects)
            if cls._scanning_total == 0:
                logging.warning("项目文件夹为空")
                cls._scanning_total = 1  # 不要让其为0
                return

            cls._scanning_curr = 0
            content_not_exist_count = 0
            cls._projects_id_queue_for_downloading_image.clear()
            # 遍历项目目录下的所有子文件夹
            for folder_name in tqdm(cls._all_projects):
                cls._scanning_curr += 1
                if cls._stop_working:
                    break
                folder_path = os.path.join(projects_dir, folder_name)
                if not os.path.isdir(folder_path):
                    continue
                json_file_path = os.path.join(folder_path, 'content.json')
                if not os.path.exists(json_file_path):
                    content_not_exist_count += 1  # content.json does not exist, add to content_not_exist_count
                    continue
                image_gallery_folder = os.path.join(folder_path, 'image_gallery', cls._image_size_type)
                # image_gallery_folder example: ./results/projects/<project_id>/image_gallery/<image_size_type>
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                image_gallery_images = data.get('image_gallery', [])
                if not image_gallery_images:
                    continue
                if not os.path.exists(image_gallery_folder):
                    cls._projects_id_queue_for_downloading_image.append(folder_name)
                    continue
                image_gallery_names = os.listdir(image_gallery_folder)
                if len(image_gallery_names) < len(image_gallery_images):
                    cls._projects_id_queue_for_downloading_image.append(folder_name)
            logging.info(
                f"已扫描{len(cls._all_projects)}个项目，其中{content_not_exist_count}个项目没有content.json文件，{len(cls._projects_id_queue_for_downloading_image)}个项目需要下载图像")
            cls._is_working = False
            cls._working_context = None

            if cls._start_after_scan:
                cls.download_gallery_images()

        threading.Thread(target=_scan_projects_folder).start()

    @classmethod
    def download_projects_html_to_local(cls):
        if cls._is_working:
            logging.warning("其他任务正在进行...")
            return

        if len(cls._projects_id_queue_for_scraping_html) == 0:
            logging.warning("没有需要下载的html文件")
            return
        # 从本地文件加载invalid_project_ids
        if os.path.exists(invalid_project_ids_path):
            with open(invalid_project_ids_path, 'r', encoding='utf-8') as f:
                invalid_project_ids = set(json.load(f))
        else:
            invalid_project_ids = set()

        def save_invalid_project_ids():
            with open(invalid_project_ids_path, 'w', encoding='utf-8') as f:
                logging.info("保存invalid_project_ids")
                json.dump(list(invalid_project_ids), f, ensure_ascii=False, indent=4)

        # 新增定时保存的函数
        def timer_save_invalid_project_ids():
            while cls._is_working:
                time.sleep(60)
                save_invalid_project_ids()

        def _download_projects_html_to_local():
            from utils.html_utils import request_project_html, flush_success_queue
            from concurrent.futures import ThreadPoolExecutor, as_completed
            cls._is_working = True
            cls._working_context = "Step1-download"
            cls._stop_working = False
            cls._working_total = len(cls._projects_id_queue_for_scraping_html)
            assert cls._working_total > 0
            cls._working_curr = 0
            g.mSuccessProjects.clear()

            def _get_html_content(project_id: str, i: int):
                if cls._stop_working:
                    return
                g.mAliveWorkers += 1
                g.mAliveProjects.append(project_id)
                g.mProjectStartTimes[project_id] = time.time()
                success = request_project_html(project_id, i, cls._working_total, invalid_project_ids,
                                               force_update=False)
                if success:
                    g.mSuccessProjects.append(project_id)
                cls._working_curr += 1
                g.mAliveWorkers -= 1
                g.mAliveProjects.remove(project_id)
                g.mProjectStartTimes.pop(project_id)

            threading.Thread(target=timer_save_invalid_project_ids).start()

            with ThreadPoolExecutor(max_workers=32) as executor:
                futures = [executor.submit(_get_html_content, project_id, i) for i, project_id in
                           enumerate(cls._projects_id_queue_for_scraping_html)]
                for future in as_completed(futures):
                    future.result()

            flush_success_queue('content_html')

            logging.info("爬取完成")
            save_invalid_project_ids()

            cls._is_working = False
            cls._working_context = None

        threading.Thread(target=_download_projects_html_to_local).start()

    @classmethod
    def parse_htmls(cls):
        if cls._is_working:
            logging.warning("其他任务正在进行...")
            return
        if len(cls._projects_id_queue_for_parsing_html) == 0:
            logging.warning("没有需要解析的html文件")
            return

        def _parse_htmls():
            from utils.html_utils import parse_project_content, flush_success_queue
            from concurrent.futures import ThreadPoolExecutor, as_completed
            cls._is_working = True
            cls._working_context = "Step2-parse"
            cls._stop_working = False
            cls._working_total = len(cls._projects_id_queue_for_parsing_html)
            assert cls._working_total > 0
            cls._working_curr = 0
            g.mSuccessProjects.clear()

            def _parse_project_content(project_id: str, i: int):
                if cls._stop_working:
                    return
                time.sleep(0.02)
                g.mAliveWorkers += 1
                g.mAliveProjects.append(project_id)
                g.mProjectStartTimes[project_id] = time.time()
                changed = parse_project_content(project_id, i, cls._working_total,
                                                flags=Flags.NONE)
                if changed:
                    g.mSuccessProjects.append(project_id)
                cls._working_curr += 1
                g.mAliveWorkers -= 1
                g.mAliveProjects.remove(project_id)
                g.mProjectStartTimes.pop(project_id)

            with ThreadPoolExecutor(max_workers=64) as executor:
                futures = []
                logging.info("正在将任务添加到队列...")
                for i, project_id in tqdm(enumerate(cls._projects_id_queue_for_parsing_html), total=cls._working_total):
                    futures.append(executor.submit(_parse_project_content, project_id, i))
                logging.info("开始解析页面内容... 如果遇到image_gallery为空的情况，可能需要等待返回image_gallery结果")
                for future in tqdm(as_completed(futures), total=len(futures)):
                    future.result()

            flush_success_queue('content_json')
            logging.info('complete')
            cls._is_working = False
            cls._working_context = None

        threading.Thread(target=_parse_htmls).start()

    @classmethod
    def download_gallery_images(cls):
        if cls._is_working:
            logging.warning("其他任务正在进行...")
            return
        if len(cls._projects_id_queue_for_downloading_image) == 0:
            logging.warning("没有需要下载图像的项目")
            return

        def _download_gallery_images():
            from utils.html_utils import download_images
            from concurrent.futures import ThreadPoolExecutor, as_completed
            cls._is_working = True
            cls._working_context = "Step3-download"
            cls._stop_working = False
            cls._working_total = len(cls._projects_id_queue_for_downloading_image)
            assert cls._working_total > 0
            cls._working_curr = 0
            g.mSuccessProjects.clear()

            def _on_img_index_change(project_id, img_index, img_total):
                g.mProjectSubCurr[project_id] = img_index
                g.mProjectSubTotal[project_id] = img_total

            def _download_images(project_id: str, i: int):
                if cls._stop_working:
                    return

                g.mAliveWorkers += 1
                g.mAliveProjects.append(project_id)
                g.mProjectStartTimes[project_id] = time.time()
                success = download_images(project_id, i, cls._working_total, cls._image_size_type,
                                          img_index_change_callback=_on_img_index_change)
                if success:
                    g.mSuccessProjects.append(project_id)
                cls._working_curr += 1
                g.mAliveWorkers -= 1
                g.mAliveProjects.remove(project_id)
                g.mProjectStartTimes.pop(project_id)

            with ThreadPoolExecutor(max_workers=32) as executor:
                futures: list[Future] = [executor.submit(_download_images, project_id, i) for i, project_id in
                                         enumerate(cls._projects_id_queue_for_downloading_image)]
                for future in as_completed(futures):
                    future.result()

            logging.info('complete')
            cls._is_working = False
            cls._working_context = None

        threading.Thread(target=_download_gallery_images).start()
