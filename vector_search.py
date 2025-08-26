# -*- coding: utf-8 -*-
# @Author  : Xinruo Wang
# @Time    : 8/12/2025 8:40 PM
# @Function: vector_search

import pymongo
import numpy as np
import logging
from pymongo import MongoClient
from utils import logging_utils
from config import *

# 初始化日志
logging_utils.init_logger("vector_search")
logger = logging.getLogger(__name__)


class VectorSearchEngine:
    def __init__(self, validate_connection=True):
        """
        初始化向量搜索引擎
        :param validate_connection: 是否验证数据库连接
        """
        try:
            # MongoDB 连接配置
            self.client = pymongo.MongoClient(user_settings.mongodb_host)
            self.db = self.client[user_settings.mongodb_archdaily_db_name]

            # 定义向量存储集合
            self.text_collection = self.db["content_embedding"]
            self.image_collection = self.db["image_embedding_default_512"]

            # 验证数据库连接
            if validate_connection:
                self._validate_connection()
                logger.info("MongoDB数据库连接验证成功")

            # 验证索引存在性
            self._validate_indexes()

            logger.info("向量搜索引擎初始化成功")
        except Exception as e:
            logger.error(f"向量搜索引擎初始化失败: {e}")
            raise

    def _validate_connection(self):
        """
        验证MongoDB连接是否成功
        """
        try:
            # 尝试列出数据库名称以验证连接
            db_names = self.client.list_database_names()
            logger.info(f"成功连接到MongoDB，可用数据库: {', '.join(db_names)}")

            # 检查目标数据库是否存在
            if user_settings.mongodb_archdaily_db_name in db_names:
                logger.info(f"找到目标数据库: {user_settings.mongodb_archdaily_db_name}")
            else:
                logger.warning(f"目标数据库 {user_settings.mongodb_archdaily_db_name} 不存在，将在首次写入时自动创建")

            # 尝试访问集合以验证权限
            collection_names = self.db.list_collection_names()
            logger.info(
                f"数据库 {user_settings.mongodb_archdaily_db_name} 中的集合: {', '.join(collection_names) if collection_names else '无集合'}")

        except Exception as e:
            logger.error(f"数据库连接验证失败: {e}")
            raise RuntimeError(f"无法连接到MongoDB数据库: {e}")

    def _validate_indexes(self):
        """
        验证必须的向量索引是否存在
        """
        required_indexes = {
            self.text_collection: "vector_index_text",
            self.image_collection: "vector_index"
        }

        for collection, index_name in required_indexes.items():
            try:
                # 首先检查常规索引
                indexes = list(collection.list_indexes())
                index_names = [idx.get("name") for idx in indexes]

                # 然后检查搜索索引
                search_indexes = list(collection.list_search_indexes())
                search_index_names = [idx.get("name") for idx in search_indexes]

                # 合并所有索引名称
                all_index_names = index_names + search_index_names

                if index_name in all_index_names:
                    if index_name in search_index_names:
                        # 找到搜索索引，检查状态
                        for s_idx in search_indexes:
                            if s_idx.get("name") == index_name:
                                status = s_idx.get("status", "unknown")
                                if status == "READY":
                                    logger.info(f"验证集合 {collection.name} 的搜索索引 {index_name} 存在且已就绪")
                                else:
                                    logger.warning(f"集合 {collection.name} 的搜索索引 {index_name} 状态为 {status}")
                                break
                    else:
                        logger.info(f"验证集合 {collection.name} 的常规索引 {index_name} 存在")
                else:
                    logger.warning(f"集合 {collection.name} 缺少向量索引 {index_name}，搜索功能可能无法正常工作")
                    if all_index_names:
                        logger.warning(f"可用的索引包括: {', '.join(all_index_names)}")
            except Exception as e:
                logger.warning(f"无法验证集合 {collection.name} 的索引: {e}")

    def get_random_vector(self, collection_name="text"):
        """
        从数据库中获取一个随机的向量样本

        :param collection_name: "text" 或 "image"
        :return: 随机向量 (numpy数组)
        """
        try:
            collection = self.text_collection if collection_name == "text" else self.image_collection

            # 获取随机文档
            pipeline = [{"$sample": {"size": 1}}]
            random_doc = next(collection.aggregate(pipeline))

            # 返回嵌入向量
            vector = np.array(random_doc["embedding"])
            logger.info(f"获取到随机向量，维度: {len(vector)}, 来自集合: {collection_name}")
            return vector
        except StopIteration:
            logger.warning(f"集合 {collection.name} 中没有文档")
            # 返回一个默认的1536维零向量
            return np.zeros(1536)
        except Exception as e:
            logger.error(f"获取随机向量失败: {e}")
            raise

    def text_vector_search(self, query_vector, top_k=5, num_candidates=150):
        """
        执行文本向量搜索

        :param query_vector: 查询向量 (numpy数组)
        :param top_k: 返回结果数量
        :param num_candidates: 候选数量
        :return: 搜索结果列表
        """
        try:
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index_text",
                        "path": "embedding",
                        "queryVector": query_vector.tolist(),
                        "numCandidates": num_candidates,
                        "limit": top_k
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "project_id": 1,
                        "text_content": 1,
                        "text_idx": 1,
                        "chunk_idx": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]

            results = list(self.text_collection.aggregate(pipeline))
            logger.info(f"文本向量搜索完成，返回 {len(results)} 个结果")
            return results
        except Exception as e:
            logger.error(f"文本向量搜索失败: {e}")
            raise

    def image_vector_search(self, query_vector, top_k=5, num_candidates=150):
        """
        执行图像向量搜索

        :param query_vector: 查询向量 (numpy数组)
        :param top_k: 返回结果数量
        :param num_candidates: 候选数量
        :return: 搜索结果列表
        """
        try:
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_vector.tolist(),
                        "numCandidates": num_candidates,
                        "limit": top_k
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "project_id": 1,
                        "image_idx": 1,
                        "chunk_idx": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]

            results = list(self.image_collection.aggregate(pipeline))
            logger.info(f"图像向量搜索完成，返回 {len(results)} 个结果")
            return results
        except Exception as e:
            logger.error(f"图像向量搜索失败: {e}")
            raise

    def get_project_content(self, project_id):
        """
        获取项目的完整内容信息

        :param project_id: 项目ID
        :return: 项目内容信息
        """
        try:
            content_collection = self.db["content_collection"]
            project_data = content_collection.find_one({"_id": project_id})
            return project_data
        except Exception as e:
            logger.error(f"获取项目内容失败: {e}")
            raise

    def search_and_display(self, collection_type="text", top_k=5):
        """
        交互式搜索测试

        :param collection_type: "text" 或 "image"
        :param top_k: 返回结果数量
        """
        try:
            # 获取随机查询向量
            random_vector = self.get_random_vector(collection_type)
            logger.info(f"使用随机查询向量 (维度: {len(random_vector)})")

            # 执行搜索
            if collection_type == "text":
                results = self.text_vector_search(random_vector, top_k)
                print(f"\n文本搜索结果 (Top {top_k}):")
                for i, res in enumerate(results, 1):
                    print(f"{i}. [相似度: {res['score']:.4f}]")
                    print(f"   项目ID: {res['project_id']}")
                    print(f"   文本索引: {res['text_idx']}, 块索引: {res['chunk_idx']}")
                    print(f"   文本片段: {res['text_content'][:100]}...")
            else:
                results = self.image_vector_search(random_vector, top_k)
                print(f"\n图像搜索结果 (Top {top_k}):")
                for i, res in enumerate(results, 1):
                    print(f"{i}. [相似度: {res['score']:.4f}]")
                    print(f"   项目ID: {res['project_id']}")
                    print(f"   图像索引: {res['image_idx']}, 块索引: {res['chunk_idx']}")

            print("\n" + "=" * 80)
            return results
        except Exception as e:
            logger.error(f"搜索显示失败: {e}")
            raise

    def close(self):
        """
        关闭数据库连接
        """
        try:
            self.client.close()
            logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接时出错: {e}")

    def get_database_info(self):
        """
        获取数据库信息
        :return: 数据库信息字典
        """
        try:
            info = {
                "host": user_settings.mongodb_host,
                "database_name": user_settings.mongodb_archdaily_db_name,
                "collections": {}
            }

            # 获取数据库中的集合信息
            collection_names = self.db.list_collection_names()
            for collection_name in collection_names:
                collection = self.db[collection_name]
                doc_count = collection.estimated_document_count()
                info["collections"][collection_name] = {
                    "document_count": doc_count
                }

            return info
        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return None


# 使用示例
if __name__ == "__main__":
    try:
        # 创建搜索引擎实例（会自动验证连接）
        search_engine = VectorSearchEngine()

        print("=" * 80)
        print("AI-Archdaily 数据库向量搜索测试")
        print("=" * 80)

        # 显示数据库连接信息
        print("\n>>> 数据库连接信息:")
        db_info = search_engine.get_database_info()
        if db_info:
            print(f"MongoDB主机: {db_info['host']}")
            print(f"数据库名称: {db_info['database_name']}")
            print("集合信息:")
            for collection_name, collection_info in db_info["collections"].items():
                print(f"  - {collection_name}: {collection_info['document_count']} 文档")

        # 测试文本搜索
        print("\n>>> 正在测试文本向量搜索...")
        search_engine.search_and_display("text", top_k=3)

        # 测试图像搜索
        print("\n>>> 正在测试图像向量搜索...")
        search_engine.search_and_display("image", top_k=3)

        # 模拟真实查询场景
        print("\n>>> 模拟真实查询场景:")
        print("1. 用户输入查询: '现代建筑立面设计'")

        # 在实际应用中，这里应该使用模型生成查询向量
        # 为了演示，我们使用数据库中的随机向量
        query_vector = search_engine.get_random_vector("text")
        print(f"2. 生成查询向量 (维度: {len(query_vector)})")

        # 执行真实搜索
        results = search_engine.text_vector_search(query_vector, top_k=3)
        print("3. 搜索结果:")
        for i, res in enumerate(results, 1):
            print(f"   {i}. 项目 {res['project_id']} (相似度: {res['score']:.4f})")

        # 获取第一个结果的完整内容
        if results:
            project_id = results[0]['project_id']
            print(f"\n>>> 获取项目 {project_id} 的完整内容...")
            project_content = search_engine.get_project_content(project_id)
            if project_content:
                print(f"项目标题: {project_content.get('title', 'N/A')}")
                print(f"项目标签: {', '.join(project_content.get('tags', []))}")
                specs = project_content.get('specs', {})
                print(f"项目信息: {specs}")

    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        print(f"错误: {e}")
    finally:
        # 关闭连接
        if 'search_engine' in locals():
            search_engine.close()
