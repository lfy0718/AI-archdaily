import os

import torch
from PIL import Image

from transformers import AutoModel, CLIPImageProcessor, AutoTokenizer

print("loading model from pretrained")
model_name = 'OpenGVLab/InternViT-300M-448px-V2_5'
cache_dir = os.path.join(os.path.dirname(__file__), "checkpoints/internViT")
model = AutoModel.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
    trust_remote_code=True,
    cache_dir=cache_dir).cuda().eval()

image = Image.open('./examples/image1.jpg').convert('RGB')
image_processor = CLIPImageProcessor.from_pretrained(model_name, cache_dir=cache_dir)

pixel_values = image_processor(images=image, return_tensors='pt').pixel_values
pixel_values = pixel_values.to(torch.bfloat16).cuda()
outputs = model(pixel_values)
# 获取最后一层的隐藏状态
last_hidden_state = outputs.last_hidden_state.to(torch.float32)  # BFloat16 to Float32
print("Last hidden state shape:", last_hidden_state.shape)

print("==================================================================")

# 加载文本模型和分词器
text_model_name = "Qwen/Qwen2.5-0.5B-Instruct"
cache_dir = os.path.join(os.path.dirname(__file__), "checkpoints/Qwen")
tokenizer = AutoTokenizer.from_pretrained(text_model_name, cache_dir=cache_dir)
text_model = AutoModel.from_pretrained(text_model_name, cache_dir=cache_dir).cuda().eval()

# 准备文本输入
text = "This is an example sentence."
inputs = tokenizer(text, return_tensors='pt')
inputs = {k: v.cuda() for k, v in inputs.items()}
outputs = text_model(**inputs)

last_hidden_state = outputs.last_hidden_state.to(torch.float32)  # BFloat16 to Float32
print("Last hidden state shape:", last_hidden_state.shape)