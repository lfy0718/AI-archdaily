# step7：建立初步的database表格
import json
import logging
import os
from datetime import datetime

import pandas as pd

# 配置日志
log_dir = f'./log/step7'
os.makedirs(log_dir, exist_ok=True)
log_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.log'
log_file_path = os.path.join(log_dir, log_filename)

# 创建一个文件处理器，设置编码为UTF-8
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter("%(levelname)-8s %(asctime)-24s %(filename)-24s:%(lineno)-4d | %(message)s"))

# 创建一个控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter("%(levelname)-8s %(asctime)-24s %(filename)-24s:%(lineno)-4d | %(message)s"))

# 获取根日志器，并添加处理器
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

projects_dir = 'results/projects'
output_dir = 'results/database'
image_size_type = 'large'  # 可选项：large, slideshow, medium
database_name = "image_database"


def main(incremental=True):
    image_database = []

    # 确保结果文件夹存在
    os.makedirs(output_dir, exist_ok=True)

    # 检查是否进行增量读取
    pkl_path = os.path.join(output_dir, f'{database_name}.pkl')
    existing_paths = set()  # 初始化existing_paths为空集合
    if incremental and os.path.exists(pkl_path):
        # 读取已有的pkl文件
        df_existing = pd.read_pickle(pkl_path)
        image_database = df_existing.to_dict(orient='records')
        # 创建一个集合来存储已存在的image_path
        existing_paths = set(item['image_path'] for item in image_database)

    # 记录初始项目数量
    initial_count = len(image_database)
    logging.info(f"existing images count: {initial_count}")
    # 遍历每个项目文件夹
    for project_folder in os.listdir(projects_dir):
        project_path = os.path.join(projects_dir, project_folder)
        content_json_path = os.path.join(project_path, 'content.json')
        image_gallery_path = os.path.join(project_path, 'image_gallery', image_size_type)
        if not os.path.isfile(content_json_path) or not os.path.isdir(image_gallery_path):
            continue

        # 读取content.json文件
        with open(content_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            image_gallery_images = data.get('image_gallery', [])
        image_missing_count = 0
        # 遍历image_gallery/<image_size_type>下的所有图片文件
        for img_index, image_gallery_image in enumerate(image_gallery_images):
            img_url = image_gallery_image.get(f'url_{image_size_type}')
            if not img_url:
                continue
            img_filename = f"{img_index:05d}.jpg"
            image_path = os.path.join(image_gallery_path, img_filename)
            if not os.path.isfile(image_path):
                image_missing_count += 1
                continue
            # 检查路径是否已经存在
            if incremental and image_path in existing_paths:
                continue
            image_database.append({
                'image_path': image_path,
                'image_url': img_url,
                'features': '',
                'project_id': project_folder
            })
        if image_missing_count > 0:
            logging.warning(
                f"[{project_folder}] image_gallery/{image_size_type} is missing {image_missing_count} images, total {len(image_gallery_images)}")

    # 创建DataFrame并保存
    df = pd.DataFrame(image_database)
    df.to_pickle(pkl_path)

    # 计算新增项目数量
    new_count = len(image_database) - initial_count

    # 打印新增项目数量和当前总项目数量
    print(f"新增图片数量: {new_count}")
    print(f"当前总图片数量: {len(image_database)}")


if __name__ == '__main__':
    main(incremental=True)
