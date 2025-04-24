# 从mongodb 检索
import numpy as np
from pymongo import MongoClient

from config import *

# 连接到MongoDB
logging.info(f"connecting {user_settings.mongodb_host}")
client = MongoClient(user_settings.mongodb_host)
client.list_database_names()
logging.info("connected")
db = client[user_settings.mongodb_archdaily_db_name]
content_collection = db['content_collection']
content_embedding_collection = db['content_embedding']


# Function to embed a query and perform a vector search
def query_and_display(query):
    def get_text_embeddings(texts, batch_size=1):
        return np.random.random((1, 1024))

    query_embedding = get_text_embeddings(query, batch_size=1)[0]
    print(query_embedding.shape)
    print("searching...")
    # Retrieve relevant child documents based on query
    child_docs = content_embedding_collection.aggregate([{
        "$vectorSearch": {
            "index": "default",
            "path": "item.embedding",
            "queryVector": query_embedding,
            "numCandidates": 10
        }
    }])
    # Fetch corresponding parent documents for additional context
    parent_docs = [content_collection.find_one({"_id": doc['project_id']}) for doc in child_docs]

    # 打印parent_docs的_id信息
    for doc in parent_docs:
        print(f"Parent Doc ID: {doc['_id']}")

    return parent_docs, child_docs


parent_docs, child_docs = query_and_display("Hello Archdaily")
