import logging
import os
import json

from tqdm import tqdm

from config import *
from pymongo import MongoClient
from bson.objectid import ObjectId
from utils.logging_utils import init_logger
init_logger("step9")

skip_exist = False

# 连接到MongoDB
client = MongoClient(user_settings.mongodb_host)
logging.info(f"connected to {user_settings.mongodb_host}")
db = client[user_settings.mongodb_db_name]

content_collection = db['content_collection']

all_projects = os.listdir(user_settings.projects_dir)[:100] # 取前100个做实验

# 遍历每个项目文件夹
for project_id in tqdm(all_projects):
    project_path = os.path.join(user_settings.projects_dir, project_id)

    # 检查数据库中是否存在该 _id
    if skip_exist:
        existing_doc = content_collection.find_one({'_id': project_id})
        if existing_doc:
            logging.info(f"project: {project_id} 已存在于数据库中，跳过处理")
            continue

    # 读取content.json
    content_json_path = os.path.join(project_path, 'content.json')
    if not os.path.exists(content_json_path):
        logging.warning(f"project: {project_id} content.json文件不存在")
        continue

    with open(content_json_path, 'r', encoding='utf-8') as f:
        content_data = json.load(f)

    # 插入或更新content数据
    content_doc = {'_id': project_id}
    content_doc.update(content_data)
    content_result = content_collection.update_one(
        {'_id': project_id},
        {'$set': content_doc},
        upsert=True  # 修改为 upsert=True，确保不存在时插入
    )

    # 区分插入和更新操作
    if content_result.upserted_id:
        logging.info(f"project: {project_id} 插入成功")
    else:
        logging.info(f"project: {project_id} 更新成功，修改计数: {content_result.modified_count}")

# 关闭MongoDB连接
client.close()
