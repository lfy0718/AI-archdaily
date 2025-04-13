import os
import pandas as pd
import numpy as np
from datetime import datetime
import shutil
from apis.cn_clip_api import get_features
from tqdm import tqdm



def main():
    input_dir = 'results/database'
    backup_dir = os.path.join(input_dir, 'backup')
    pkl_path = os.path.join(input_dir, 'image_database.pkl')
    
    # 确保备份目录存在
    os.makedirs(backup_dir, exist_ok=True)
    
    # 备份文件
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_path = os.path.join(backup_dir, f'image_database.pkl.{timestamp}.backup')
    shutil.copy2(pkl_path, backup_path)
    print(f'Backup created at {backup_path}')
    
    # 读取pkl文件
    print('Reading image_database.pkl...')
    df = pd.read_pickle(pkl_path)
    
    # 遍历DataFrame，填充空的cn_clip_vector
    for index, row in tqdm(df.iterrows()):
        if pd.isna(row['cn_clip_vector']) or row['cn_clip_vector'] == '':
            image_path = row['image_path']
            try:
                feature_vector = get_features(image_path)
                df.at[index, 'cn_clip_vector'] = feature_vector
            except Exception as e:
                print(f'Error processing {image_path}: {e}')
    
    # 保存更新后的DataFrame
    df.to_pickle(pkl_path)
    print(f'Image_database.pkl updated. {pkl_path}')

if __name__ == '__main__':
    main()