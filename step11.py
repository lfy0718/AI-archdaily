# 从mongodb 检索
import numpy as np
from pymongo import MongoClient
from utils import logging_utils
from config import *
logging_utils.init_logger("step11")
# 连接到MongoDB
logging.info(f"connecting {user_settings.mongodb_host}")
client = MongoClient(user_settings.mongodb_host)
client.list_database_names()

db = client[user_settings.mongodb_archdaily_db_name]
logging.info(f"connected to {user_settings.mongodb_archdaily_db_name}")
content_collection = db['content_collection']
content_embedding_collection = db['content_embedding']
cursor = content_embedding_collection.list_search_indexes()
for index in cursor:
    print(index)

# Function to embed a query and perform a vector search
def query_and_display(query):
    def get_text_embeddings(texts, batch_size=1):
        from temp_data import data
        return np.array(data["embedding"]).reshape((1, -1))

    query_embedding = get_text_embeddings(query, batch_size=1)[0]
    print(query_embedding.shape)

    # Retrieve relevant child documents based on query
    pipeline = [
        {
            '$vectorSearch': {
                'index': 'vector_index',
                'path': 'embedding',
                'queryVector': query_embedding.tolist(),
                'numCandidates': 150,
                'limit': 10
            }
        },
        {
            '$project': {
                '_id': 0,
                'project_id': 1,
                'text_content': 1,
                'score': {'$meta': 'vectorSearchScore'}
            }
        }

    ]
    print("searching...")
    child_docs = content_embedding_collection.aggregate(pipeline)
    # Fetch corresponding parent documents for additional context
    # parent_docs = [content_collection.find_one({"_id": doc['project_id']}) for doc in child_docs]

    # 打印parent_docs的_id信息
    for doc in child_docs:
        print(doc)

    # return parent_docs, child_docs


query_and_display("Hello Archdaily")
