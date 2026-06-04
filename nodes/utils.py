import os
from pathlib import Path


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
