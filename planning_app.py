# -*- coding: utf-8 -*-
# @Author  : Xinruo Wang
# @Time    : 10/25/2025 8:40 PM
# @Function: AI planning前端
"""
智能设计策划系统 - Gradio用户界面
"""
import gradio as gr
import sys

sys.path.append('.')

# 导入配置和工具
from config import user_settings
from planning_utils import PlanningAgent


def create_ui():
    """创建Gradio界面"""

    # 初始化Agent
    agent = PlanningAgent(user_settings)

    def process_query(query: str, show_steps: bool):
        """
        处理用户输入

        参数：
            query: 用户需求描述
            show_steps: 是否显示调试信息

        返回：
            (策划书Markdown, 图片列表)
        """
        if not query.strip():
            return "❌ 请输入建筑需求描述", []

        # 执行策划流程
        report, image_paths = agent.run(query)

        # 添加调试信息
        if show_steps:
            debug_info = f"\n\n---\n### 📊 调试信息\n"
            debug_info += f"- 图片数量: {len(image_paths)}\n"
            report = report + debug_info

        return report, image_paths

    # 构建Gradio界面
    with gr.Blocks(
            title="智能建筑设计策划系统",
            theme=gr.themes.Soft()
    ) as demo:

        gr.Markdown("""
        # 🏗️ 智能建筑设计策划系统
        ### 基于MongoDB向量检索 + Qwen3的AI策划工具
        ---
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📝 输入建筑需求")

                query_input = gr.Textbox(
                    label="需求描述",
                    placeholder="例如：我要在山脚下建一座24个班的小学",
                    lines=5
                )

                show_steps = gr.Checkbox(
                    label="显示处理步骤（调试模式）",
                    value=False
                )

                submit_btn = gr.Button("🚀 生成策划书", variant="primary", size="lg")

                gr.Markdown("""
                ### 💡 使用提示
                - 描述建筑类型、地理位置、规模
                - 系统会从数据库检索相关案例
                - 生成专业的设计策划书
                """)

            with gr.Column(scale=2):
                gr.Markdown("### 📄 设计策划书")
                report_output = gr.Markdown(value="*策划书将在这里显示...*")

                gr.Markdown("### 🖼️ 参考案例图片")
                gallery_output = gr.Gallery(columns=3, rows=2, height=450)

        submit_btn.click(
            fn=process_query,
            inputs=[query_input, show_steps],
            outputs=[report_output, gallery_output]
        )

        gr.Examples(
            examples=[
                ["我要在山脚下建一座24个班的小学"],
                ["海边度假酒店，100间客房，现代简约风格"],
                ["城市商业综合体，购物+餐饮+娱乐"],
            ],
            inputs=query_input
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(share=True, server_name="0.0.0.0")