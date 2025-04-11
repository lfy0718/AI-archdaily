import json
import os
from tqdm import tqdm

# 定义保存结果的目录
pages_dir = 'results/pages'
output_dir = './results/projects'

# 确保输出目录存在
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 遍历results/projects目录下的所有JSON文件
for file_name in os.listdir(pages_dir):
    if file_name.endswith('.json'):
        file_path = os.path.join(pages_dir, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取results字段
        results = data.get('results', [])
        
        # 遍历每个result
        for result in tqdm(results):
            document_id = result.get('document_id')
            if document_id:
                # 创建以document_id命名的文件夹
                folder_path = os.path.join(output_dir, str(document_id))
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                
                # 保存result为JSON文件
                output_file_path = os.path.join(folder_path, f'{document_id}.json')
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)
                # print(f'Saved {output_file_path}')