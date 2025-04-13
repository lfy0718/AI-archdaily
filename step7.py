# step7：建立初步的database表格
import os
import pandas as pd
import hashlib

from tqdm import tqdm

projects_dir = 'results/projects'
output_dir = 'results/database'


def calculate_image_hash(image_path):
    """计算图片的哈希值"""
    with open(image_path, 'rb') as f:
        image_data = f.read()
        return hashlib.md5(image_data).hexdigest()


def main(incremental=True):
    image_database = []

    # 确保结果文件夹存在
    os.makedirs(output_dir, exist_ok=True)

    # 检查是否进行增量读取
    pkl_path = os.path.join(output_dir, 'image_database.pkl')
    existing_paths = set()  # 初始化existing_paths为空集合
    if incremental and os.path.exists(pkl_path):
        # 读取已有的pkl文件
        df_existing = pd.read_pickle(pkl_path)
        image_database = df_existing.to_dict(orient='records')
        # 创建一个集合来存储已存在的image_path
        existing_paths = set(item['image_path'] for item in image_database)

    # 记录初始项目数量
    initial_count = len(image_database)

    # 遍历每个项目文件夹
    for project_folder in tqdm(os.listdir(projects_dir)):
        project_path = os.path.join(projects_dir, project_folder)
        image_path = os.path.join(project_path, 'large.jpg')

        if os.path.isfile(image_path):  # 如果存在large.jpg(封面图)
            # 检查路径是否已经存在
            if incremental and image_path in existing_paths:
                continue

            image_hash = calculate_image_hash(image_path)
            image_database.append({
                'image_path': image_path,
                'image_hash': image_hash,
                'image_url': '',
                'cn_clip_vector': ''
            })

    # 创建DataFrame并保存
    df = pd.DataFrame(image_database)
    df.to_pickle(pkl_path)

    # 计算新增项目数量
    new_count = len(image_database) - initial_count

    # 打印新增项目数量和当前总项目数量
    print(f"新增项目数量: {new_count}")
    print(f"当前总项目数量: {len(image_database)}")


if __name__ == '__main__':
    main(incremental=True)
