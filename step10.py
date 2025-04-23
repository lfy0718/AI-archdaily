import numpy as np
from pymongo import MongoClient
from pymongo import MongoClient
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tqdm import tqdm

from config import *
from utils.logging_utils import init_logger

init_logger("step10")
skip_exist = True

# 连接到MongoDB
client = MongoClient(user_settings.mongodb_host)
logging.info(f"connected to {user_settings.mongodb_host}")
db = client[user_settings.mongodb_db_name]
content_collection = db['content_collection']
content_embedding_collection = db['content_embedding']

# 初始化文本分割器
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,  # 每段最大长度
    chunk_overlap=50  # 段与段之间的重叠长度
)


def get_features(text):
    """
    模拟获取文本的嵌入向量（1024维）
    实际使用时应替换为真实的嵌入模型
    """
    # 假设返回一个随机的1024维向量
    return np.random.rand(1024)


# 遍历每个项目
all_projects = os.listdir(user_settings.archdaily_projects_dir)[:100]  # 取前100个做实验
for project_id in tqdm(all_projects):
    # 判断当前 project_id 是否已存在于 content_embedding_collection 中
    existing_embeddings = content_embedding_collection.count_documents({'project_id': project_id})

    # 根据用户选项决定是否跳过或覆盖
    if existing_embeddings > 0:
        if skip_exist:
            logging.info(f"project: {project_id} 已存在于 content_embedding_collection 中，跳过处理")
            continue
        else:
            # 删除所有与当前 project_id 相关的文档
            content_embedding_collection.delete_many({'project_id': project_id})
            logging.info(f"project: {project_id} 已存在于 content_embedding_collection 中，删除现有数据并重新处理")

    # 从content_collection中提取main_content
    content_doc = content_collection.find_one({'_id': project_id})
    if not content_doc or 'main_content' not in content_doc:
        logging.warning(f"project: {project_id} 没有main_content字段")
        continue

    main_content = content_doc['main_content']
    text_contents = [item['content'] for item in main_content if item['type'] == 'text']

    # 处理每个text内容
    for text_idx, text in enumerate(text_contents):
        # 使用langchain分割文本
        chunks = text_splitter.split_text(text)
        for chunk_idx, chunk in enumerate(chunks):
            # 获取嵌入向量
            embedding_vector = get_features(chunk)

            # 插入到content_embedding集合
            embedding_doc = {
                'project_id': project_id,
                'embedding': embedding_vector.tolist(),  # 转换为列表以便存储
                'text_content': chunk,
                'text_idx': text_idx,
                'chunk_idx': chunk_idx
            }
            result = content_embedding_collection.insert_one(embedding_doc)
            logging.info(f"project: {project_id} 插入embedding成功，_id: {result.inserted_id}")

# 关闭MongoDB连接
client.close()
