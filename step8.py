# 使用cn_clip补全image_database中尚未计算的图片特征向量
import logging
import os
import time
import pandas as pd
from datetime import datetime
import shutil

from PIL import Image
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

import apis.cn_clip_api

# 配置日志
log_dir = f'./log/step8'
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


database_name = "image_database"
get_features_func = apis.cn_clip_api.get_image_features

input_dir = 'results/database'
backup_dir = os.path.join(input_dir, 'backup')
pkl_path = os.path.join(input_dir, f'{database_name}.pkl')

# 确保备份目录存在
os.makedirs(backup_dir, exist_ok=True)

# 备份文件
timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
backup_path = os.path.join(backup_dir, f'{database_name}.pkl.{timestamp}.backup')
shutil.copy2(pkl_path, backup_path)
logging.info(f'Backup created at {backup_path}')

# 读取pkl文件
logging.info(f'Reading {database_name}.pkl...')
df = pd.read_pickle(pkl_path)

# 筛选出需要处理的行
rows_to_process = df[df['features'].apply(lambda x: isinstance(x, str))]
logging.info(f"{len(rows_to_process)} rows need to be processed. total = {len(df)}")
time.sleep(1)




def process_row(index, row, df):
    image_path = row['image_path']
    try:
        image = Image.open(image_path)
        feature_vector = get_features_func(image)
        df.at[index, 'features'] = feature_vector
    except Exception as e:
        logging.error(f'Error processing {image_path}: {e}')


# 并发处理
with ThreadPoolExecutor(max_workers=32) as executor:  # 根据显存设置
    futures = [executor.submit(process_row, index, row, df) for index, row in rows_to_process.iterrows()]
    for future in tqdm(as_completed(futures), total=len(futures)):
        future.result()

# 保存更新后的DataFrame
df.to_pickle(pkl_path)
logging.info(f'{database_name}.pkl updated. {pkl_path}')

