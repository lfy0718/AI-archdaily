# -*- coding: utf-8 -*-
# @Author  : Xinruo Wang
# @Time    : 10/25/2025 8:40 PM
# @Function: AI planning后端
"""
智能设计策划系统 - 工具函数模块
功能：MongoDB向量检索、图片检索、Qwen API调用、策划生成
"""
import os
import sys
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import MongoClient
from openai import OpenAI
from datetime import datetime

# 确保可以导入项目模块
#sys.path.append('.')


class VectorSearchManager:
    """
    MongoDB向量检索管理器
    负责：文本向量化 + MongoDB Vector Search
    """

    def __init__(self, config):
        """
        初始化向量检索管理器

        参数：
            config: 配置对象（来自config.py的user_settings）
        """
        self.config = config
        print(f"\n{'=' * 60}")
        print(f"🔌 正在初始化向量检索系统...")
        print(f"{'=' * 60}")

        # 连接MongoDB
        try:
            self.mongo_client = MongoClient(
                config.mongodb_host,
                serverSelectionTimeoutMS=5000
            )
            self.mongo_client.server_info()  # 测试连接

            self.db = self.mongo_client[config.mongodb_archdaily_db_name]
            # 只需要content_embedding集合
            self.embedding_collection = self.db['content_embedding']

            # 统计数据
            embedding_count = self.embedding_collection.count_documents({})

            print(f"✅ MongoDB连接成功！")
            print(f"   数据库: {config.mongodb_archdaily_db_name}")
            print(f"   向量数据数: {embedding_count}")

        except Exception as e:
            print(f"❌ MongoDB连接失败: {e}")
            raise

        # 初始化Qwen客户端
        self.qwen_client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        print(f"✅ Qwen客户端初始化成功")
        print(f"{'=' * 60}\n")

    def get_text_embedding(self, text: str) -> List[float]:
        """
        使用Qwen将文本转为1536维向量

        参数：
            text: 要向量化的文本

        返回：
            1536维向量列表
        """
        try:
            response = self.qwen_client.embeddings.create(
                model="text-embedding-v3",
                input=text
            )
            embedding = response.data[0].embedding
            print(f"   ✓ 向量化: {text[:50]}... → {len(embedding)}维")
            return embedding

        except Exception as e:
            print(f"❌ 向量化失败: {e}")
            return []

    def vector_search(self, query_text: str, top_k: int = 5) -> List[Dict]:
        """
        【核心方法】MongoDB向量检索

        工作流程：
        1. 将查询文本向量化（Qwen Embedding）
        2. 在MongoDB中进行向量相似度搜索
        3. 返回最相关的文本块

        参数：
            query_text: 查询文本
            top_k: 返回结果数量

        返回：
            匹配的文档列表
        """
        print(f"\n📊 MongoDB向量检索")
        print(f"   查询: \"{query_text}\"")
        print(f"   目标数量: {top_k}")

        # Step 1: 向量化查询文本
        query_embedding = self.get_text_embedding(query_text)
        if not query_embedding:
            print(f"❌ 查询文本向量化失败")
            return []

        # Step 2: 构建MongoDB Vector Search聚合查询
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.config.vector_search_index_name,   # 向量索引名称
                    "path": "embedding",  # 向量字段名
                    "queryVector": query_embedding,
                    "numCandidates": top_k * 10,
                    "limit": top_k
                }
            },
            {
                "$project": {
                    "project_id": 1,
                    "text_content": 1,
                    "text_idx": 1,
                    "chunk_idx": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]

        try:
            # 执行查询
            results = list(self.embedding_collection.aggregate(pipeline))
            print(f"✅ 找到 {len(results)} 条相关结果")

            # 格式化结果
            formatted_results = []
            for doc in results:
                formatted_results.append({
                    'project_id': doc.get('project_id'),
                    'text_content': doc.get('text_content', ''),
                    'text_idx': doc.get('text_idx'),
                    'chunk_idx': doc.get('chunk_idx'),
                    'similarity_score': doc.get('score', 0)
                })
                print(f"   - 项目{doc.get('project_id')} | "
                      f"分数:{doc.get('score', 0):.3f} | "
                      f"{doc.get('text_content', '')[:50]}...")

            return formatted_results

        except Exception as e:
            print(f"❌ 向量检索失败: {e}")
            print(f"   提示: 请确保已在MongoDB中创建向量搜索索引")
            print(f"   索引名称: vector_index")
            print(f"   索引字段: embedding (1536维)")
            return []


class ImageSearchManager:
    """
    图片检索管理器（使用CN-CLIP）
    负责：根据关键词检索相似图片
    """

    def __init__(self, config):
        """
        初始化图片检索管理器

        参数：
            config: 配置对象
        """
        self.config = config
        print(f"\n{'=' * 60}")
        print(f"🖼️  正在初始化图片检索系统...")
        print(f"{'=' * 60}")

        try:
            # 加载图像特征数据库
            pkl_path = 'results/database/image_database.pkl'
            self.image_df = pd.read_pickle(pkl_path)
            self.image_df = self.image_df[
                self.image_df['features'].apply(lambda x: isinstance(x, np.ndarray))
            ]
            self.image_df['features'] = self.image_df['features'].apply(
                lambda x: x.squeeze()
            )
            self.image_features = np.stack(self.image_df['features'].values)

            print(f"✅ 图像数据库加载成功！")
            print(f"   图片数: {len(self.image_df)}")
            print(f"   特征维度: {self.image_features.shape}")
        except Exception as e:
            print(f"❌ 图像数据库加载失败: {e}")
            raise

        print(f"{'=' * 60}\n")

    def search_similar_images(self, keywords: List[str], top_k: int = 6) -> List[Dict]:
        """
        根据关键词检索相似图像

        参数：
            keywords: 关键词列表
            top_k: 返回图片数量

        返回：
            包含图片路径和项目ID的字典列表
        """
        # 导入cn_clip_api
        try:
            from apis import cn_clip_api
        except ImportError as e:
            print(f"❌ 无法导入cn_clip_api: {e}")
            return []

        # 合并关键词
        query_text = " ".join(keywords)
        print(f"\n🔍 图片检索")
        print(f"   查询: \"{query_text}\"")

        try:
            # 使用CN-CLIP提取文本特征
            text_features = cn_clip_api.get_text_features(query_text)

            if text_features.ndim == 1:
                text_features = text_features.reshape(1, -1)

            # 计算相似度
            similarities = cosine_similarity(text_features, self.image_features)
            top_indices = np.argsort(similarities[0])[-top_k:][::-1]

            # 构建结果
            results = []
            for idx in top_indices:
                row = self.image_df.iloc[idx]
                image_path = self._get_full_image_path(row)

                # 检查文件是否存在
                if not os.path.exists(image_path):
                    print(f"⚠️  图片不存在: {image_path}")
                    continue

                results.append({
                    'image_path': image_path,
                    'project_id': row['project_id'],
                    'similarity': float(similarities[0][idx])
                })

            print(f"✅ 找到 {len(results)} 张相似图片")
            return results

        except Exception as e:
            print(f"❌ 图片检索失败: {e}")
            return []

    def _get_full_image_path(self, row) -> str:
        """获取图片完整路径"""
        image_name = os.path.basename(row['image_path'])
        return os.path.join(
            self.config.archdaily_projects_dir,
            row['project_id'],
            "image_gallery/large",
            image_name
        )


class QwenAPIClient:
    """Qwen3 API客户端 - 负责所有大模型对话"""

   def __init__(self):
    """初始化Qwen客户端"""
    try:
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY") or "sk-05dba08497cf465f9e4b9ca1a25bb973",  # ✅ 添加默认值
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = "qwen-plus"
        print(f"✅ Qwen对话模型初始化成功 ({self.model})")
    except Exception as e:
        print(f"❌ Qwen客户端初始化失败: {e}")
        raise


    def _call_api(self, prompt: str, system_prompt: str = None,
                  temperature: float = 0.7) -> str:
        """调用Qwen API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"❌ Qwen API调用失败: {e}")
            return ""

    def extract_keywords(self, user_query: str) -> List[str]:
        """【步骤1】提取关键词"""
        print(f"\n{'=' * 60}")
        print(f"📍 步骤1: 提取关键词")
        print(f"{'=' * 60}")

        prompt = f"""
请从以下建筑需求中提取3-5个核心关键词，用于数据库检索。

要求：
1. 提取建筑类型、地理特征、规模、功能等核心信息
2. 关键词要具体、准确
3. 只返回关键词，用逗号分隔，不要其他解释

用户需求：{user_query}

关键词："""

        response = self._call_api(prompt, temperature=0.3)
        keywords = [kw.strip() for kw in response.split(',') if kw.strip()]
        print(f"🔑 提取到的关键词: {keywords}")
        print(f"{'=' * 60}\n")
        return keywords

    def generate_design_points(self, user_query: str, context: str) -> str:
        """【步骤2】生成设计要点"""
        print(f"\n{'=' * 60}")
        print(f"📍 步骤2: 生成设计要点")
        print(f"{'=' * 60}")

        system_prompt = "你是一位资深建筑设计顾问，擅长分析建筑需求并提出专业建议。"

        prompt = f"""
根据以下信息，为用户的建筑需求提供5-8个核心设计要点。

用户需求：
{user_query}

参考案例（来自数据库检索）：
{context if context else "暂无参考案例"}

要求：
1. 每个要点单独一行，格式为"数字. 要点标题: 简要说明"
2. 要点应具体、可操作
3. 包含：选址、功能布局、环境适应、美学风格等
4. 每个要点30-50字

设计要点："""

        response = self._call_api(prompt, system_prompt, temperature=0.7)
        print(f"📝 生成的设计要点:\n{response}")
        print(f"{'=' * 60}\n")
        return response

    def extract_keywords_from_points(self, design_points: str) -> List[str]:
        """【步骤3】提取视觉关键词"""
        print(f"\n{'=' * 60}")
        print(f"📍 步骤3: 提取视觉关键词")
        print(f"{'=' * 60}")

        prompt = f"""
从以下设计要点中提取5-8个**视觉相关**的关键词，用于建筑图片检索。

要求：
1. 关键词应该是具体的建筑元素、风格特征
2. 适合用于图片搜索（如"坡屋顶"、"庭院"、"木结构"）
3. 只返回关键词，用逗号分隔

设计要点：
{design_points}

关键词："""

        response = self._call_api(prompt, temperature=0.3)
        keywords = [kw.strip() for kw in response.split(',') if kw.strip()]
        print(f"🎨 视觉关键词: {keywords}")
        print(f"{'=' * 60}\n")
        return keywords

    def generate_final_report(self, user_query: str, design_points: str,
                              images: List[Dict], reference_cases: str = "") -> str:
        """【步骤4】生成最终策划书"""
        print(f"\n{'=' * 60}")
        print(f"📍 步骤4: 生成策划书")
        print(f"{'=' * 60}")

        image_info = "\n".join([
            f"- 图片{i + 1}: 项目{img['project_id']} (相似度: {img['similarity']:.2f})"
            for i, img in enumerate(images)
        ])

        system_prompt = "你是一位资深建筑设计策划师，擅长撰写专业的设计策划书。"

        prompt = f"""
请撰写一份专业的建筑设计策划书。

## 用户需求
{user_query}

## 设计要点
{design_points}

## 参考案例
{reference_cases if reference_cases else "（基于专业知识）"}

## 可用图片
{image_info}

## 撰写要求
1. **格式**: Markdown，包含标题和段落
2. **结构**: 项目概述 → 设计理念 → 设计要点详述 → 参考案例
3. **插图**: 在合适位置插入 [IMAGE_0]、[IMAGE_1]... 最多{len(images)}张
4. **字数**: 800-1200字
5. **风格**: 专业、简洁、有洞察力

开始撰写："""

        response = self._call_api(prompt, system_prompt, temperature=0.8)
        print(f"📄 策划书生成完成 (约 {len(response)} 字)")
        print(f"{'=' * 60}\n")
        return response


class PlanningAgent:
    """策划Agent - 协调整个流程"""

    def __init__(self, config):
        """
        初始化策划Agent

        参数：
            config: 配置对象（来自config.py的user_settings）
        """
        print(f"\n{'#' * 60}")
        print(f"🚀 初始化智能策划Agent")
        print(f"{'#' * 60}\n")

        self.vector_search = VectorSearchManager(config)
        self.image_search = ImageSearchManager(config)
        self.qwen_client = QwenAPIClient()

        print(f"✅ Agent初始化完成！\n")

    def run(self, user_query: str) -> Tuple[str, List[str]]:
        """
        执行完整策划流程

        参数：
            user_query: 用户输入的建筑需求

        返回：
            (策划书Markdown, 图片路径列表)
        """
        print(f"\n{'#' * 60}")
        print(f"🎯 开始处理用户需求")
        print(f"   需求: {user_query}")
        print(f"{'#' * 60}\n")

        try:
            # Step 1: 提取关键词
            keywords = self.qwen_client.extract_keywords(user_query)
            if not keywords:
                return "❌ 关键词提取失败", []

            # Step 2: MongoDB向量检索（核心！）
            query_text = " ".join(keywords)
            search_results = self.vector_search.vector_search(query_text, top_k=5)

            # 格式化检索结果
            reference_cases = self._format_search_results(search_results)

            # Step 3: 生成设计要点
            design_points = self.qwen_client.generate_design_points(
                user_query, reference_cases
            )
            if not design_points:
                return "❌ 设计要点生成失败", []

            # Step 4: 提取视觉关键词
            image_keywords = self.qwen_client.extract_keywords_from_points(design_points)
            if not image_keywords:
                image_keywords = keywords

            # Step 5: 图片检索
            images = self.image_search.search_similar_images(image_keywords, top_k=6)

            # Step 6: 生成策划书
            report = self.qwen_client.generate_final_report(
                user_query, design_points, images, reference_cases
            )

            # Step 7: 插入图片
            report_with_images, image_paths = self._insert_images(report, images)

            print(f"\n{'#' * 60}")
            print(f"✅ 策划完成！")
            print(f"   策划书长度: {len(report_with_images)} 字符")
            print(f"   插入图片: {len(image_paths)} 张")
            print(f"{'#' * 60}\n")

            return report_with_images, image_paths

        except Exception as e:
            error_msg = f"❌ 处理出错: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return error_msg, []

    def _format_search_results(self, results: List[Dict]) -> str:
        """格式化检索结果"""
        if not results:
            return ""

        formatted = []
        for i, doc in enumerate(results[:3], 1):
            text = doc.get('text_content', '')
            if len(text) > 200:
                text = text[:200] + "..."
            formatted.append(
                f"参考案例{i} (项目{doc.get('project_id')}): {text}"
            )

        return "\n\n".join(formatted)

    def _insert_images(self, report: str, images: List[Dict]) -> Tuple[str, List[str]]:
        """插入图片"""
        image_paths = [img['image_path'] for img in images]

        for i, img in enumerate(images):
            placeholder = f"[IMAGE_{i}]"
            markdown_image = f"\n\n![参考案例{i + 1}]({img['image_path']})\n"
            markdown_image += f"*参考案例 {i + 1} - 项目{img['project_id']} (相似度: {img['similarity']:.2f})*\n\n"
            report = report.replace(placeholder, markdown_image)

        return report, image_paths