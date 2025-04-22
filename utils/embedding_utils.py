# -*- coding: utf-8 -*-
# @Author  : Yiheng Feng
# @Time    : 4/22/2025 3:04 PM
# @Function:
import base64
import time
from http import HTTPStatus
from typing import Optional

import dashscope

from config import *

_last_request_times = {api_key: -1.0 for api_key in user_settings.api_keys}
def embed_text(text, api_key) -> tuple[Optional[list], int]:
    # https://bailian.console.aliyun.com/?tab=api#/api/?type=model&url=https%3A%2F%2Fhelp.aliyun.com%2Fdocument_detail%2F2712517.html
    # 文本:
    #   - 语言/格式: 中英文文本
    #   - 长度限制: 最多512个Token，超过部分会被自动截断

    while True:
        if time.time() - _last_request_times[api_key] > 0.5:
            break
        time.sleep(0.1)

    _last_request_times[api_key] = time.time()
    resp = dashscope.MultiModalEmbedding.call(
        model="multimodal-embedding-v1",
        input=[{'text': text}],
        api_key=api_key
    )

    if resp.status_code == 200:
        embedding = resp.output['embeddings'][0]["embedding"]
        return embedding, resp.status_code
    return None, resp.status_code


def embed_image(image_path, api_key):
    # 图片:
    #   - 格式: JPG、PNG、BMP
    #   - 输入方式: 支持Base64编码或URL形式
    #   - 大小限制: 最大3MB
    while True:
        if time.time() - _last_request_times[api_key] > 0.5:
            break
        time.sleep(0.1)
    image_format = image_path.split(".")[-1]
    with open(image_path, "rb") as image_file:
        # 读取文件并转换为Base64
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    image_data = f"data:image/{image_format};base64,{base64_image}"
    # 调用模型接口
    resp = dashscope.MultiModalEmbedding.call(
        model="multimodal-embedding-v1",
        input=[{'image': image_data}],
        api_key=api_key
    )
    if resp.status_code == HTTPStatus.OK:
        embedding = resp.output['embeddings'][0]["embedding"]
        return embedding, resp.status_code
    return None, resp.status_code
