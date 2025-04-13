import os

import torch
from PIL import Image
from transformers import AutoModel, CLIPImageProcessor
from transformers import AutoTokenizer

model_name = 'OpenGVLab/InternVL-14B-224px'
cache_dir = os.path.join(os.path.dirname(__file__), "checkpoints/internVL")

model = AutoModel.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
    trust_remote_code=True,
    cache_dir=cache_dir).cuda().eval()
# https://huggingface.co/OpenGVLab/InternVL-14B-224px/blob/main/modeling_internvl.py
# class InternVLModel(InternVLPreTrainedModel):

image_processor = CLIPImageProcessor.from_pretrained(model_name, cache_dir=cache_dir)

tokenizer = AutoTokenizer.from_pretrained(
    model_name, use_fast=False, add_eos_token=True,trust_remote_code=True, cache_dir=cache_dir)
tokenizer.pad_token_id = 0  # set pad_token_id to 0

images = [
    Image.open('./examples/image1.jpg').convert('RGB'),
    Image.open('./examples/image2.jpg').convert('RGB'),
    Image.open('./examples/image3.jpg').convert('RGB')
]
prefix = 'summarize:'
texts = [
    prefix + 'a photo of a red panda',  # English
    prefix + '一张熊猫的照片',  # Chinese
    prefix + '二匹の猫の写真'  # Japanese
]

pixel_values = image_processor(images=images, return_tensors='pt').pixel_values
pixel_values = pixel_values.to(torch.bfloat16).cuda()
input_ids = tokenizer(texts, return_tensors='pt', max_length=80,
                      truncation=True, padding='max_length').input_ids.cuda()

# InternVL-C
logits_per_image, logits_per_text = model(
    image=pixel_values, text=input_ids, mode='InternVL-C')
probs = logits_per_image.softmax(dim=-1)
# tensor([[9.9609e-01, 5.2185e-03, 6.0070e-08],
#         [2.2949e-02, 9.7656e-01, 5.9903e-06],
#         [3.2932e-06, 7.4863e-05, 1.0000e+00]], device='cuda:0',
#        dtype=torch.bfloat16, grad_fn=<SoftmaxBackward0>)
print(probs)
# # InternVL-G
# logits_per_image, logits_per_text = model(
#     image=pixel_values, text=input_ids, mode='InternVL-G')
# probs = logits_per_image.softmax(dim=-1)
# # tensor([[9.9609e-01, 3.1738e-03, 3.6322e-08],
# #         [8.6060e-03, 9.9219e-01, 2.8759e-06],
# #         [1.7583e-06, 3.1233e-05, 1.0000e+00]], device='cuda:0',
# #        dtype=torch.bfloat16, grad_fn=<SoftmaxBackward0>)
#
# # please set add_eos_token to False for generation
# tokenizer.add_eos_token = False
# image = Image.open('./examples/image1.jpg').convert('RGB')
# pixel_values = image_processor(images=image, return_tensors='pt').pixel_values
# pixel_values = pixel_values.to(torch.bfloat16).cuda()
#
# tokenized = tokenizer("English caption:", return_tensors='pt')
# pred = model.generate(
#     pixel_values=pixel_values,
#     input_ids=tokenized.input_ids.cuda(),
#     attention_mask=tokenized.attention_mask.cuda(),
#     num_beams=5,
#     min_new_tokens=8,
# )
# caption = tokenizer.decode(pred[0].cpu(), skip_special_tokens=True).strip()
# # English caption: a red panda sitting on top of a wooden platform
# print(caption)