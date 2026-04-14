import os
from pathlib import Path
import torch
from PIL import Image
import numpy as np


def get_default_output_dir():
    """获取 ComfyUI 的默认输出目录
    
    Returns:
        str: 默认输出目录的绝对路径
    """
    current_file = os.path.abspath(__file__)
    comfyui_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    return os.path.join(comfyui_root, "output")


def ensure_absolute_path(path_str, default_to_cwd=True):
    """确保路径是绝对路径
    
    Args:
        path_str: 路径字符串，如果为 None 或空字符串，则使用当前工作目录
        default_to_cwd: 当路径为空时，是否默认使用当前工作目录
    
    Returns:
        Path: 绝对路径对象
    """
    if not path_str:
        if default_to_cwd:
            path = Path.cwd()
        else:
            path = Path()
    else:
        path = Path(path_str)
    
    if not path.is_absolute():
        path = Path.cwd() / path
    
    return path


def ensure_parent_directory(file_path):
    """确保文件的父目录存在
    
    Args:
        file_path: 文件路径对象
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)


class SaveStringToTextNode:
    @classmethod
    def INPUT_TYPES(cls):
        comfyui_output_dir = get_default_output_dir()
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "forceInput": True}),
                "file_name": ("STRING", {"default": "output", "multiline": False}),
                "extension": ("STRING", {"default": "txt", "multiline": False}),
                "encoding": (["utf-8", "gbk", "utf-16", "ascii"], {"default": "utf-8"}),
                "save_mode": (["single_file", "multiple_files"], {"default": "single_file"}),
            },
            "optional": {
                "directory_path": ("STRING", {"default": comfyui_output_dir, "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("file_path",)
    OUTPUT_NODE = True
    FUNCTION = "save_string_to_file"
    CATEGORY = "Utils"

    def save_string_to_file(self, text, file_name, extension="txt", encoding="utf-8", save_mode="single_file", directory_path=""):
        try:
            if save_mode == "single_file":
                # 单文件模式：所有内容保存到一个文件（在for循环中追加）
                full_file_name = f"{file_name}.{extension}"
                abs_path = ensure_absolute_path(directory_path) / full_file_name
                ensure_parent_directory(abs_path)
                
                # 检查文件是否已存在且不为空
                file_exists = abs_path.exists() and abs_path.stat().st_size > 0
                
                with open(abs_path, "a" if file_exists else "w", encoding=encoding) as f:
                    # 如果是追加模式且文件不为空，添加换行符
                    if file_exists:
                        f.write("\n")
                    f.write(text)
                
                return (str(abs_path),)
            else:
                # 多文件模式：每个提示词保存到不同文件（适配for循环）
                # 分割文本为单个提示词（按换行符分割）
                prompts = [p.strip() for p in text.split("\n") if p.strip()]
                
                if not prompts:
                    raise Exception("No valid prompts found in text")
                
                # 使用自定义扩展名
                file_stem = file_name
                
                saved_paths = []
                
                for i, prompt in enumerate(prompts, 1):
                    # 生成带序号的文件名
                    new_file_name = f"{file_stem}_{i}.{extension}"
                    abs_path = ensure_absolute_path(directory_path) / new_file_name
                    ensure_parent_directory(abs_path)
                    
                    with open(abs_path, "w", encoding=encoding) as f:
                        f.write(prompt)
                    
                    saved_paths.append(str(abs_path))
                
                # 返回第一个文件路径作为主输出
                return (saved_paths[0],)
        except Exception as e:
            raise Exception(f"Error saving file: {str(e)}")


class SaveImageToFolderNode:
    @classmethod
    def INPUT_TYPES(cls):
        comfyui_output_dir = get_default_output_dir()
        return {
            "required": {
                "images": ("IMAGE",),
                "file_name": ("STRING", {"default": "", "multiline": False}),
                "image_format": (["png", "jpg", "jpeg", "webp"], {"default": "png"}),
            },
            "optional": {
                "output_folder": ("STRING", {"default": comfyui_output_dir, "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("folder_path",)
    OUTPUT_NODE = True
    FUNCTION = "save_images"
    CATEGORY = "Utils"

    def save_images(self, images, file_name="", image_format="png", output_folder=""):
        try:
            # 确定输出文件夹
            output_folder = ensure_absolute_path(output_folder)
            
            # 创建输出文件夹
            output_folder.mkdir(parents=True, exist_ok=True)
            
            # 处理图像
            saved_files = []
            for i, image in enumerate(images):
                # 转换图像格式
                img = 255. * image.cpu().numpy()
                img = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
                
                # 生成文件名
                if file_name and file_name.strip() != "":
                    # 使用输入的文件名直接命名
                    filename = f"{file_name}.{image_format}"
                    file_path = output_folder / filename
                else:
                    # 文件名为空时，使用默认递增规则
                    counter = 1
                    while True:
                        filename = f"image_{counter}.{image_format}"
                        file_path = output_folder / filename
                        if not file_path.exists():
                            break
                        counter += 1
                
                # 保存图像
                img.save(file_path, format=image_format.upper())
                saved_files.append(str(file_path))
            
            return (str(output_folder),)
        except Exception as e:
            raise Exception(f"Error saving images: {str(e)}")


class LoadTextFilesNode:
    """
    从文件夹中批量加载 txt 文件的节点
    
    功能：
    - max_files: 设置要加载的 txt 文件最大数量
    - index: 配合 for 循环使用，从 0 到 max_files-1，依次加载对应的文件
    - 每次执行只加载 1 个文件，输出文件内容和文件名
    
    使用示例：
    - 设置 max_files=10，配合 for 循环（count=10）
    - for 循环的 index 连接到节点的 index 输入
    - 每次循环会依次加载第 0、1、2...9 个文件
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        comfyui_output_dir = get_default_output_dir()
        return {
            "required": {
                "folder_path": ("STRING", {"default": comfyui_output_dir, "multiline": False}),
                "max_files": ("INT", {
                    "default": 10, 
                    "min": 1, 
                    "max": 999, 
                    "step": 1,
                    "display": "number"
                }),
                "index": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 999, 
                    "step": 1,
                    "display": "number"
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "file_name")
    FUNCTION = "load_text_file"
    CATEGORY = "Utils"
    OUTPUT_NODE = True

    def load_text_file(self, folder_path, max_files, index):
        """
        加载指定索引的 txt 文件
        
        Args:
            folder_path: txt 文件所在的文件夹路径
            max_files: 最大文件数量限制
            index: 要加载的文件索引（从 0 开始）
            
        Returns:
            tuple: (文件内容，文件名)
        """
        try:
            # 确保路径是绝对路径
            folder = ensure_absolute_path(folder_path)
            
            # 检查文件夹是否存在
            if not folder.exists():
                raise Exception(f"Folder does not exist: {str(folder)}")
            
            if not folder.is_dir():
                raise Exception(f"Path is not a directory: {str(folder)}")
            
            # 获取所有 txt 文件并按名称排序
            txt_files = sorted([f for f in folder.iterdir() if f.is_file() and f.suffix.lower() == '.txt'])
            
            if not txt_files:
                raise Exception(f"No .txt files found in folder: {str(folder)}")
            
            # 限制文件数量（只取前 max_files 个文件）
            txt_files = txt_files[:max_files]
            
            # 检查索引是否超出范围
            if index >= len(txt_files):
                raise Exception(f"Index {index} is out of range. Only {len(txt_files)} file(s) found (max_files: {max_files})")
            
            # 获取指定索引的文件
            selected_file = txt_files[index]
            
            # 读取文件内容
            with open(selected_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 输出调试信息
            print(f"[LoadTextFilesNode] 加载文件 ({index+1}/{max_files}): {selected_file.name}")
            print(f"[LoadTextFilesNode] 文件路径：{selected_file}")
            print(f"[LoadTextFilesNode] 内容长度：{len(content)} 字符")
            
            # 返回文本内容和文件名
            return (content, selected_file.name)
        except Exception as e:
            print(f"[LoadTextFilesNode] 错误：{str(e)}")
            raise Exception(f"Error loading text file: {str(e)}")