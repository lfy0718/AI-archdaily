# test_search_index.py
from pymongo import MongoClient
from config import user_settings

# 连接到MongoDB
client = MongoClient(user_settings.mongodb_host)
db = client[user_settings.mongodb_archdaily_db_name]

# 检查content_embedding集合的常规索引
collection = db["content_embedding"]
print(f"数据库: {user_settings.mongodb_archdaily_db_name}")
print(f"集合: content_embedding")

print("\n=== 常规索引 ===")
try:
    indexes = list(collection.list_indexes())
    print("所有常规索引:")
    for index in indexes:
        print(f"  - 名称: {index['name']}, 类型: {index.get('type', 'N/A')}")
        if 'fields' in index:
            print(f"    字段: {index['fields']}")
except Exception as e:
    print(f"获取常规索引时出错: {e}")

# 检查搜索索引（包括向量搜索索引）
print("\n=== 搜索索引 ===")
try:
    search_indexes = list(collection.list_search_indexes())
    if search_indexes:
        print("所有搜索索引:")
        for index in search_indexes:
            print(f"  - 名称: {index.get('name', 'N/A')}")
            print(f"    状态: {index.get('status', 'N/A')}")
            print(f"    查询映射器: {index.get('latestDefinition', {}).get('mappings', 'N/A')}")
            print(f"    类型: {index.get('type', 'N/A')}")
    else:
        print("没有找到搜索索引")

    # 检查是否有vector_index_text索引
    vector_index_found = False
    for index in search_indexes:
        if index.get('name') == 'vector_index_text':
            vector_index_found = True
            print("\n✓ 找到 vector_index_text 搜索索引")
            print(f"  状态: {index.get('status')}")
            break

    if not vector_index_found:
        print("\n✗ 未找到 vector_index_text 搜索索引")
        # 列出所有搜索索引名称
        search_index_names = [idx.get('name') for idx in search_indexes]
        if search_index_names:
            print(f"  可用的搜索索引: {', '.join(search_index_names)}")

except Exception as e:
    print(f"获取搜索索引时出错: {e}")