import os

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


def get_features(image_path):
    image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image)
        # 对特征进行归一化，请使用归一化后的图文特征用于下游任务
        image_features /= image_features.norm(dim=-1, keepdim=True)
        return image_features.detach().cpu().numpy()  # 返回numpy格式
