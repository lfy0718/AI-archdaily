# see https://huggingface.co/OpenGVLab/InternVL2_5-1B
import os

import numpy as np
import torch
import torch.nn.functional as F
import torchvision.transforms as T
from PIL import Image
from torchvision.transforms.functional import InterpolationMode
from transformers import AutoModel, AutoTokenizer

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def build_transform(input_size):
    MEAN, STD = IMAGENET_MEAN, IMAGENET_STD
    transform = T.Compose([
        T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
        T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=MEAN, std=STD)
    ])
    return transform


def find_closest_aspect_ratio(aspect_ratio, target_ratios, width, height, image_size):
    best_ratio_diff = float('inf')
    best_ratio = (1, 1)
    area = width * height
    for ratio in target_ratios:
        target_aspect_ratio = ratio[0] / ratio[1]
        ratio_diff = abs(aspect_ratio - target_aspect_ratio)
        if ratio_diff < best_ratio_diff:
            best_ratio_diff = ratio_diff
            best_ratio = ratio
        elif ratio_diff == best_ratio_diff:
            if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                best_ratio = ratio
    return best_ratio


def dynamic_preprocess(image, min_num=1, max_num=12, image_size=448, use_thumbnail=False):
    orig_width, orig_height = image.size
    aspect_ratio = orig_width / orig_height

    # calculate the existing image aspect ratio
    target_ratios = set(
        (i, j) for n in range(min_num, max_num + 1) for i in range(1, n + 1) for j in range(1, n + 1) if
        i * j <= max_num and i * j >= min_num)
    target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])

    # find the closest aspect ratio to the target
    target_aspect_ratio = find_closest_aspect_ratio(
        aspect_ratio, target_ratios, orig_width, orig_height, image_size)

    # calculate the target width and height
    target_width = image_size * target_aspect_ratio[0]
    target_height = image_size * target_aspect_ratio[1]
    blocks = target_aspect_ratio[0] * target_aspect_ratio[1]
    # resize the image
    resized_img = image.resize((target_width, target_height))
    processed_images = []
    for i in range(blocks):
        box = (
            (i % (target_width // image_size)) * image_size,
            (i // (target_width // image_size)) * image_size,
            ((i % (target_width // image_size)) + 1) * image_size,
            ((i // (target_width // image_size)) + 1) * image_size
        )
        # split the image
        split_img = resized_img.crop(box)
        processed_images.append(split_img)
    assert len(processed_images) == blocks
    if use_thumbnail and len(processed_images) != 1:
        thumbnail_img = image.resize((image_size, image_size))
        processed_images.append(thumbnail_img)
    return processed_images


def load_image(image: Image.Image, input_size=448, max_num=12):
    image = image.convert('RGB')
    transform = build_transform(input_size=input_size)
    images = dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
    pixel_values = [transform(image) for image in images]
    pixel_values = torch.stack(pixel_values)
    return pixel_values


print("loading model from pretrained...")
model_name = 'OpenGVLab/InternVL2_5-1B'
cache_dir = os.path.join(os.path.dirname(__file__), "checkpoints/internVL")
model = AutoModel.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
    trust_remote_code=True,
    cache_dir=cache_dir).eval().cuda()
# type(model) = InternVLChatModel
# see https://github.com/OpenGVLab/InternVL/blob/main/internvl_chat/internvl/model/internvl_chat/modeling_internvl_chat.py
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True, use_fast=False)


def split_and_pad_tensor(tensor, max_length=256):
    """
    Split the tensor into chunks of max_length and pad the last chunk if necessary.
    Args:
        tensor (torch.Tensor): The input tensor of shape [1, n, 896].
        max_length (int): The maximum length of each chunk.
    Returns:
        torch.Tensor: The split and padded tensor of shape [m, max_length, 896].
    """
    batch_size, seq_length, embed_dim = tensor.shape
    assert batch_size == 1, "Batch size must be 1"

    # Calculate the number of chunks
    num_chunks = (seq_length + max_length - 1) // max_length  # Ceiling division

    # Initialize the list to hold the chunks
    chunks = []

    # Split the tensor into chunks
    for i in range(num_chunks):
        start_idx = i * max_length
        end_idx = min((i + 1) * max_length, seq_length)
        chunk = tensor[:, start_idx:end_idx, :]

        # Pad the chunk if it is not long enough
        if chunk.shape[1] < max_length:
            chunk = F.pad(chunk, (0, 0, 0, max_length - chunk.shape[1]), mode='constant', value=0)

        chunks.append(chunk)

    # Stack the chunks into a single tensor
    result_tensor = torch.cat(chunks, dim=0)
    return result_tensor


def get_image_features(image: Image.Image) -> np.ndarray:
    pixel_values = load_image(image, max_num=4).to(torch.bfloat16).cuda()
    vit_embeds = model.extract_feature(pixel_values)  # [n, 256, 896] n数量在1-5之间，如果是5则表示4张局部图像+1张完整图像
    vit_embeds = F.normalize(vit_embeds, p=2, dim=-1)  # normalize
    return vit_embeds.detach().cpu().to(torch.float32).numpy().astype(np.float16)  # [n, 256, 896] n ∈ [1, 5]


def get_text_features(text: str) -> np.ndarray:
    inputs = tokenizer(text, return_tensors='pt')
    input_ids = inputs.input_ids.cuda()
    input_embeds = model.language_model.get_input_embeddings()(input_ids)  # [1, n, 896], n表示有多少token
    input_embeds = F.normalize(input_embeds, p=2, dim=-1)  # normalize
    padded_chunks = split_and_pad_tensor(input_embeds, max_length=256)  # [m, 256, 896] 切分并对齐到256, m表示有多少段落
    return padded_chunks.detach().cpu().to(torch.float32).numpy().astype(np.float16)  # [m, 256, 896]


def get_text_features_raw(text: str) -> np.ndarray:
    inputs = tokenizer(text, return_tensors='pt')
    input_ids = inputs.input_ids.cuda()
    input_embeds = model.language_model.get_input_embeddings()(input_ids)  # [1, n, 896], n表示有多少token
    return input_embeds.detach().cpu().to(torch.float32).numpy().astype(np.float16)  # [1, n, 896]


if __name__ == '__main__':
    image = Image.open("./examples/image1.jpg")
    text = """
        for i in range(num_chunks):
            start_idx = i * max_length
            end_idx = min((i + 1) * max_length, seq_length)
            chunk = tensor[:, start_idx:end_idx, :]
    
            # Pad the chunk if it is not long enough
            if chunk.shape[1] < max_length:
                chunk = F.pad(chunk, (0, 0, 0, max_length - chunk.shape[1]), mode='constant', value=0)
    
            chunks.append(chunk)
    
        # Stack the chunks into a single tensor
        result_tensor = torch.cat(chunks, dim=0)
        return result_tensor
    def get_image_features(image: Image.Image) -> np.ndarray:
        pixel_values = load_image(image, max_num=4).to(torch.bfloat16).cuda()
        vit_embeds = model.extract_feature(pixel_values)
        return vit_embeds.detach().cpu().to(torch.float32).numpy().astype(np.float16)  # [5, 256, 896]  4张局部图像+1张完整图像, 图像数量在1到5之间
    
    def get_text_features(text: str) -> np.ndarray:
        inputs = tokenizer(text, return_tensors='pt')
        input_ids = inputs.input_ids.cuda()
        input_embeds = model.language_model.get_input_embeddings()(input_ids)
        padded_chunks = split_and_pad_tensor(input_embeds, max_length=256)
        return padded_chunks.detach().cpu().to(torch.float32).numpy().astype(np.float16)
        """
    image_feature = get_image_features(image)
    print(image_feature.shape)
    text_feature = get_text_features(text)
    print(text_feature.shape)
