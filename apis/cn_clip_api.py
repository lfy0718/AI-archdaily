import os

import PIL
import cn_clip.clip as clip
import numpy as np
import torch
from PIL import Image
from cn_clip.clip import load_from_name, available_models

print("Available models:", available_models())
# Available models: ['ViT-B-16', 'ViT-L-14', 'ViT-L-14-336', 'ViT-H-14', 'RN50']

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"device = {device}")
model, preprocess = load_from_name("ViT-H-14",
                                   device=device,
                                   download_root=os.path.join(os.path.dirname(__file__), "checkpoints")
                                   )
model.eval()


def get_image_features(image: PIL.Image.Image) -> np.ndarray:
    image_tensor = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_tensor)
        # 对特征进行归一化，请使用归一化后的图文特征用于下游任务
        image_features /= image_features.norm(dim=-1, keepdim=True)
        return image_features.detach().cpu().numpy()  # 返回numpy格式 [1, 1024]


def get_text_features(text: str) -> np.ndarray:
    text_tensor = clip.tokenize([text]).to(device)
    with torch.no_grad():
        text_features = model.encode_text(text_tensor)
        # 对特征进行归一化，请使用归一化后的图文特征用于下游任务
        text_features /= text_features.norm(dim=-1, keepdim=True)
        return text_features.detach().cpu().numpy()  # [1, 1024]
