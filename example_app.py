import gradio as gr
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from apis import cn_clip_api
from config import *


# 读取image_database.pkl文件
def load_database():
    pkl_path = 'results/database/image_database.pkl'
    df = pd.read_pickle(pkl_path)

    # 过滤并展平向量
    df = df[df['features'].apply(lambda x: isinstance(x, np.ndarray))]
    df['features'] = df['features'].apply(
        lambda x: x.squeeze()  # 去除单维度
    )
    return df


# 在程序启动时加载DataFrame
df = load_database()
print(f"成功加载 {len(df)} 条有效数据")  # 添加验证输出
image_features: np.ndarray = np.stack(df['features'].values)
print(image_features.shape)


# 计算图像特征向量
def compute_image_features(image) -> np.ndarray:
    from PIL import Image
    import io

    # 确保图像被正确处理为PIL Image格式
    if isinstance(image, str):
        image = Image.open(image)
    elif isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    elif isinstance(image, io.BytesIO):
        image = Image.open(image)

    # 计算特征向量
    feature_vector = cn_clip_api.get_image_features(image)

    # 确保 feature_vector 是二维数组
    if feature_vector.ndim == 1:
        feature_vector = feature_vector.reshape(1, -1)

    return feature_vector  # [1, 1024]


# 计算文本特征向量（dummy函数）
def compute_text_features(text):
    # 计算特征向量
    feature_vector = cn_clip_api.get_text_features(text)

    # 确保 feature_vector 是二维数组
    if feature_vector.ndim == 1:
        feature_vector = feature_vector.reshape(1, -1)
    print(feature_vector.shape)
    return feature_vector  # 


# 匹配最相似的图像
def find_similar_items(image_feature_vector, text_feature_vector, negative_text_feature_vector, df, image_weight,
                       text_weight, negative_text_weight, top_k=10):
    # 确保 feature_vectors 是二维数组
    if image_feature_vector is not None and image_feature_vector.ndim == 1:
        image_feature_vector = image_feature_vector.reshape(1, -1)
    if text_feature_vector is not None and text_feature_vector.ndim == 1:
        text_feature_vector = text_feature_vector.reshape(1, -1)
    if negative_text_feature_vector is not None and negative_text_feature_vector.ndim == 1:
        negative_text_feature_vector = negative_text_feature_vector.reshape(1, -1)

    # 计算有效权重
    total_weight = sum([w for w in [image_weight, text_weight, negative_text_weight] if w is not None])
    if total_weight == 0:
        total_weight = 1  # 避免除以零

    # 计算每种特征向量的加权相似度
    weighted_similarities = 0
    if image_feature_vector is not None:
        image_similarities = cosine_similarity(image_feature_vector, image_features)
        weighted_similarities += (image_weight / total_weight) * image_similarities
    if text_feature_vector is not None:
        text_similarities = cosine_similarity(text_feature_vector, image_features)
        weighted_similarities += (text_weight / total_weight) * text_similarities
    if negative_text_feature_vector is not None:
        negative_text_similarities = cosine_similarity(negative_text_feature_vector, image_features)
        weighted_similarities -= (negative_text_weight / total_weight) * negative_text_similarities

    # 获取最相似的top_k个索引
    top_indices = np.argsort(weighted_similarities[0])[-top_k:][::-1]
    # 返回最相似的行
    return df.iloc[top_indices]


# Gradio界面
with gr.Blocks() as iface:
    gr.Markdown("# Archdaily相似项目匹配")  # 添加标题
    gr.Markdown(f"当前数据库图片数：{len(df)}")  # 添加当前数据库图片数显示

    with gr.Row():
        with gr.Column():
            image_input = gr.Image(label="上传图像", elem_id="image_input", height=400)
            text_input = gr.Textbox(label="输入文本")
            negative_text_input = gr.Textbox(label="输入负向提示文本")

            # 添加卷展栏到左半部分
            with gr.Accordion("高级参数", open=False):
                top_k_slider = gr.Slider(1, 50, value=10, step=1, label="Top K 数量")
                image_weight_slider = gr.Slider(0, 1, value=0.8, step=0.1, label="图像权重")
                text_weight_slider = gr.Slider(0, 1, value=0.3, step=0.1, label="正向提示文本权重")
                negative_text_weight_slider = gr.Slider(0, 1, value=0.2, step=0.1, label="负向提示文本权重")

            submit_button = gr.Button("匹配相似项目")
        with gr.Column():
            output_gallery = gr.Gallery(label="相似图像", columns=3, rows=2, object_fit="contain")
            go_button = gr.Button("打开选中的项目", interactive=False)

    selected_id_state = gr.State(None)  # 使用State保存选中ID


    # Gallery选择事件处理
    def on_gallery_select(evt: gr.SelectData):  # 修改: 添加参数 evt
        selected_data = evt.value  # 修改: 从事件对象中获取选中的数据
        print(selected_data)
        if selected_data and 'caption' in selected_data:
            print(selected_data['caption'])
            return selected_data['caption']
        return None


    output_gallery.select(
        on_gallery_select,
        outputs=[selected_id_state]
    )


    # 按钮点击事件处理
    def on_go_click(project_id):
        if project_id:
            import webbrowser
            webbrowser.open(f"https://www.archdaily.com/{project_id}")
            return f"打开选中的项目 (https://www.archdaily.com/{project_id})"
        return "打开选中的项目"


    selected_id_state.change(
        fn=lambda pid: gr.update(interactive=bool(pid)),
        inputs=[selected_id_state],
        outputs=[go_button]
    )
    go_button.click(
        on_go_click,
        inputs=[selected_id_state],
        outputs=None
    )


    # 更新按钮标签的逻辑移到这里
    def update_go_button_label(pid):
        if pid:
            return gr.update(value=f"打开选中的项目 (https://www.archdaily.com/{pid})")
        else:
            return gr.update(value="打开选中的项目")


    selected_id_state.change(
        fn=update_go_button_label,
        inputs=[selected_id_state],
        outputs=[go_button]
    )


    # 定义提交按钮
    def process_input(image, text, negative_text, top_k, image_weight, text_weight, negative_text_weight):
        image_feature_vector = compute_image_features(image) if image is not None else None
        text_feature_vector = compute_text_features(text) if text else None
        negative_text_feature_vector = compute_text_features(negative_text) if negative_text else None

        similar_items = find_similar_items(image_feature_vector, text_feature_vector, negative_text_feature_vector, df,
                                           image_weight, text_weight, negative_text_weight, top_k=top_k)
        # 处理空结果并返回图片路径和 project id 的列表
        result_list = []
        for _, row in similar_items.iterrows():
            image_path = row['image_path']
            image_name = os.path.basename(image_path)
            project_id = row['project_id']
            image_path = os.path.join(user_settings.archdaily_projects_dir, project_id, "image_gallery/large",
                                      image_name)
            result_list.append((image_path, row['project_id']))
        return result_list


    submit_button.click(
        process_input,
        inputs=[image_input, text_input, negative_text_input, top_k_slider, image_weight_slider, text_weight_slider,
                negative_text_weight_slider],
        outputs=output_gallery
    )


# 修改Gallery格式化函数
def format_gallery_output(result_list):
    return [{
        "image": image_path,
        "project_id": project_id
    } for image_path, project_id in result_list]


if __name__ == "__main__":
    iface.launch(share=True)  # 设置 share=True 以创建公共链接
