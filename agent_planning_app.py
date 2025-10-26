# agent_planning_app.py
import gradio as gr
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import re
import json
from typing import List, Tuple, Dict
import os

# 新增导入
from openai import OpenAI

from apis import cn_clip_api
from config import *


# 读取image_database.pkl文件
def load_database():
    pkl_path = 'results/database/image_database.pkl'
    if not os.path.exists(pkl_path):
        # 创建示例数据以防数据库不存在
        return pd.DataFrame({
            'project_id': [],
            'features': [],
            'image_path': [],
            'tags': []
        })

    df = pd.read_pickle(pkl_path)

    # 过滤并展平向量
    df = df[df['features'].apply(lambda x: isinstance(x, np.ndarray))]
    df['features'] = df['features'].apply(
        lambda x: x.squeeze() if x.ndim > 1 else x  # 去除单维度
    )
    return df


# 在程序启动时加载DataFrame
try:
    df = load_database()
    if len(df) > 0:
        image_features: np.ndarray = np.stack(df['features'].values)
    else:
        image_features = np.array([])
except Exception as e:
    print(f"加载数据库时出错: {e}")
    df = pd.DataFrame({
        'project_id': [],
        'features': [],
        'image_path': [],
        'tags': []
    })
    image_features = np.array([])

print(f"成功加载 {len(df)} 条有效数据")


# 计算文本特征向量
def compute_text_features(text):
    if not text:
        return None
    # 计算特征向量
    feature_vector = cn_clip_api.get_text_features(text)

    # 确保 feature_vector 是二维数组
    if feature_vector.ndim == 1:
        feature_vector = feature_vector.reshape(1, -1)
    return feature_vector


# 从用户输入中提取设计要点
def extract_design_points(user_input: str) -> List[str]:
    """
    从用户输入中提取关键设计要点
    """
    # 关键词模式
    patterns = [
        r"(\d+\s*个班)",
        r"(小学|中学|幼儿园|大学|学院)",
        r"(山脚|山坡|山顶|海边|城市|郊区|乡村)",
        r"(现代|传统|简约|欧式|中式|日式|美式|工业风)",
        r"(\d+\s*(平方米|平米|㎡|公顷))",
        r"(绿色|环保|可持续|节能|太阳能|雨水收集)",
        r"(开放式|封闭式|庭院|天井|中庭)",
        r"(\d+\s*(层|楼))",
        r"(多功能|复合|综合|一体化)",
        r"(景观|绿化|花园|公园|庭院)"
    ]

    design_points = []
    for pattern in patterns:
        matches = re.findall(pattern, user_input, re.IGNORECASE)
        design_points.extend(matches)

    # 添加整个输入作为备选
    if not design_points:
        design_points.append(user_input)

    return design_points


# 提取关键词
def extract_keywords(design_points: List[str]) -> List[str]:
    """
    从设计要点中提取关键词用于检索
    """
    keywords = []
    for point in design_points:
        # 简单分词
        words = re.findall(r'\w+', point.lower())
        keywords.extend(words)
    return list(set(keywords))  # 去重


# 匹配最相似的项目
def find_similar_items(text_feature_vectors: List[np.ndarray],
                       df: pd.DataFrame,
                       image_features: np.ndarray,
                       top_k: int = 5) -> pd.DataFrame:
    """
    根据多个文本特征向量检索最相似的项目
    """
    if len(df) == 0 or len(image_features) == 0:
        return pd.DataFrame()

    # 计算每个文本向量与所有图像的相似度
    all_similarities = []
    for feature_vector in text_feature_vectors:
        if feature_vector is not None:
            similarities = cosine_similarity(feature_vector, image_features)
            all_similarities.append(similarities[0])

    if not all_similarities:
        return pd.DataFrame()

    # 平均所有相似度得分
    avg_similarities = np.mean(all_similarities, axis=0)

    # 获取最相似的top_k个索引
    top_indices = np.argsort(avg_similarities)[-top_k:][::-1]

    # 返回最相似的行
    return df.iloc[top_indices]


# 生成策划书内容
def generate_proposal_content(user_input: str,
                            design_points: List[str],
                            relevant_projects: pd.DataFrame) -> str:
    """
    生成设计策划书内容 - 使用阿里云百炼qwen3-max模型
    """
    # 构造输入给大模型的prompt
    project_descriptions = []
    for _, row in relevant_projects.iterrows():
        project_descriptions.append(f"项目ID: {row['project_id']}")

    prompt = f"""
作为一名专业的建筑设计师AI助手，请基于用户输入的需求、设计要点及参考案例，生成一份结构完整、内容专业的建筑设计策划书。策划书应严格遵循建筑行业的逻辑框架，突出设计策略与技术可行性，并体现对场地、功能、空间及可持续性的综合考量：

用户需求：{user_input}

设计要点：
{chr(10).join(f'- {point}' for point in design_points)}

参考案例：
{chr(10).join(project_descriptions)}

请按照以下结构生成策划书：

# 项目概述
简要描述项目背景和目标
背景分析：结合项目区位、场地条件（地形、气候、周边环境）、规划限制及业主需求，说明项目立项的必要性与核心挑战
目标定位：明确项目类型（如文化、商业、住宅等）、规模（用地面积、建筑面积）及核心目标（如提升区域形象、满足功能复合化需求等）

# 设计理念
阐述设计理念和灵感来源
概念生成：阐述设计灵感的来源（如地域文脉、自然意象、社会需求），并提炼为可贯穿全程的设计主题（例如“流动的庭院”“光的容器”等）
策略相应：说明设计如何通过空间组织、形态构成、材料选择等具体手段回应用地特征和功能需求

# 功能布局
详细说明各功能区域的设计
总平面规划：分析建筑体量与场地的关系，包括出入口设置、交通流线（人车分流）、景观系统及与城市空间的衔接
功能布局：详细列明各功能区（如公共区域、服务空间、交通核）的面积分配、平面布局及流线逻辑，强调功能间的关联与隔离

# 空间特色
突出项目的独特设计元素
立体构成：描述建筑形态的生成逻辑（如体块切割、叠加、镂空），并分析立面设计（材质、肌理、色彩）与内部功能的对应关系
特色空间：重点突出核心空间（如中庭、屋顶花园、过渡空间）的设计手法，说明其如何增强体验感与标识性


# 技术参数
列出关键技术指标和规格
关键指标：列出容积率、建筑密度、绿地率、节能率等经济技术指标
专项设计：简述结构选型（框架/剪力墙/钢结构）、主要材料（如预制混凝土、Low-E玻璃）及设备系统（暖通、消防、智能化）的初步方案

# 可持续性设计
说明环保和可持续性措施
绿色技术：说明被动式设计（如自然通风、遮阳）与主动技术（如太阳能光伏、雨水回收）的结合方式
环境融合：强调设计在生态保护（如植被保留、微气候调节）与低碳运维方面的具体措施

# 效果预期
描述建成后的效果和影响
空间效果：描述建成后预期的空间氛围、使用效率及人文价值
社会及经济影响：分析项目对区域发展的贡献（如提升公共性、激发商业活力），并可附简要投资估算

请用专业而易懂的建筑学语言撰写，字数在1500-3500字之间。
"""

    # 调用阿里云百炼qwen3-max模型
    try:
        import os
        from openai import OpenAI

        # 从配置中获取API密钥（需要在config.py中添加）
        api_key = getattr(user_settings, 'qwen_api_key', None)
        if not api_key:
            raise ValueError("请在config.py中配置qwen_api_key")

        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        completion = client.chat.completions.create(
            model="qwen3-max",
            messages=[
                {"role": "system", "content": "你是一个专业的建筑设计师AI助手，擅长撰写建筑设计策划书。"},
                {"role": "user", "content": prompt},
            ],
            stream=False  # 不使用流式输出，便于处理
        )

        response = completion.choices[0].message.content
        return response

    except Exception as e:
        print(f"调用大模型时出错: {e}")
        # 出错时返回模拟内容
        mock_response = f"""
# 项目概述

根据您的需求——{user_input}，我们提出以下设计方案。该项目旨在创造一个满足功能需求并具有独特设计感的建筑空间。

# 设计理念

设计灵感来源于您提出的需求要点，结合现代建筑设计理念，打造功能完善、环境友好的建筑空间。

# 功能布局

1. **主要功能区**：根据需求合理规划各功能区域
2. **辅助功能区**：配套服务设施区域
3. **交通流线**：优化人流和物流组织

# 空间特色

- 结合设计要点创造独特空间体验
- 注重功能与美学的平衡
- 考虑未来发展和扩展性

# 技术参数

- 根据需求确定关键技术指标
- 符合相关建筑规范和标准
- 采用适宜的建筑材料和技术

# 可持续性设计

- 节能环保措施
- 绿色建筑技术应用
- 可持续发展理念贯彻

# 效果预期

项目建成后将满足使用需求，成为具有示范意义的建筑作品。
        """
        return mock_response



# 处理用户输入并生成完整策划方案
def process_user_request(user_input: str, top_k: int = 5) -> Tuple[str, List[Tuple[str, str]]]:
    """
    处理用户请求，生成完整的策划方案
    """
    if not user_input:
        return "请输入您的设计需求", []

    # 1. 提取设计要点
    design_points = extract_design_points(user_input)

    # 2. 提取关键词
    keywords = extract_keywords(design_points)

    # 3. 计算关键词特征向量
    text_feature_vectors = []
    for keyword in keywords[:5]:  # 限制关键词数量避免过多计算
        vector = compute_text_features(keyword)
        if vector is not None:
            text_feature_vectors.append(vector)

    # 4. 检索相关项目
    if len(df) > 0 and len(image_features) > 0:
        relevant_projects = find_similar_items(text_feature_vectors, df, image_features, top_k)
    else:
        relevant_projects = pd.DataFrame()

    # 5. 生成策划书内容
    proposal_content = generate_proposal_content(user_input, design_points, relevant_projects)

    # 6. 准备相关图片
    relevant_images = []
    if len(relevant_projects) > 0:
        for _, row in relevant_projects.iterrows():
            image_path = row['image_path']
            image_name = os.path.basename(image_path)
            project_id = row['project_id']
            full_image_path = os.path.join(
                user_settings.archdaily_projects_dir,
                project_id,
                "image_gallery/large",
                image_name
            )
            # 检查图片是否存在
            if os.path.exists(full_image_path):
                relevant_images.append((full_image_path, project_id))
            else:
                # 如果特定图片不存在，使用占位符
                relevant_images.append(("https://via.placeholder.com/300x200?text=Project+" + project_id, project_id))
    else:
        # 如果没有相关项目，添加占位符图片
        for i in range(min(3, top_k)):
            relevant_images.append((
                "https://via.placeholder.com/300x200?text=Sample+Design",
                f"sample_{i}"
            ))

    return proposal_content, relevant_images


# Gradio界面
with gr.Blocks(title="智能建筑策划Agent") as iface:
    gr.Markdown("# 🏛️ 智能建筑策划Agent")
    gr.Markdown("输入您的建筑设计需求，AI将自动生成策划方案并推荐相关案例")

    with gr.Row():
        with gr.Column(scale=1):
            user_input = gr.Textbox(
                label="📝 请输入您的设计需求",
                placeholder="例如：我要在山脚下建一座24个班的小学...",
                lines=3
            )

            with gr.Accordion("⚙️ 高级参数", open=False):
                top_k_slider = gr.Slider(
                    1, 10, value=5, step=1,
                    label="推荐案例数量"
                )

            submit_btn = gr.Button(
                "🚀 生成策划方案",
                variant="primary"
            )

            gr.Examples(
                examples=[
                    "我要在山脚下建一座24个班的小学",
                    "设计一个海边的现代化美术馆",
                    "在城市中心建造一个绿色办公大楼",
                    "设计一所可容纳500人的寄宿制高中"
                ],
                inputs=user_input,
                label="💡 示例输入"
            )

        with gr.Column(scale=2):
            output_text = gr.Markdown(label="📋 策划方案")
            output_gallery = gr.Gallery(
                label="🖼️ 相关设计案例",
                columns=3,
                rows=2,
                object_fit="cover",
                height="auto"
            )


    # 处理函数
    def handle_request(user_input_text, k_value):
        return process_user_request(user_input_text, k_value)


    # 绑定事件
    submit_btn.click(
        handle_request,
        inputs=[user_input, top_k_slider],
        outputs=[output_text, output_gallery]
    )

    # 回车键触发
    user_input.submit(
        handle_request,
        inputs=[user_input, top_k_slider],
        outputs=[output_text, output_gallery]
    )

if __name__ == "__main__":
    iface.launch(share=True)