"""
触发词配置管理模块
封装触发词配置文件的所有读写操作
"""

import json
from pathlib import Path
import folder_paths


def get_config_file_path() -> Path:
    """获取触发词配置文件路径

    Returns:
        Path: 配置文件绝对路径
    """
    current_dir = Path(__file__).parent
    return current_dir / "lora_trigger_words.json"


def load_trigger_words() -> dict:
    """加载触发词配置文件

    Returns:
        dict: 触发词配置字典 {lora_filename: trigger_word}
    """
    config_path = get_config_file_path()
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_trigger_words(config: dict) -> None:
    """保存触发词配置到文件

    Args:
        config: 触发词配置字典 {lora_filename: trigger_word}
    """
    config_path = get_config_file_path()
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"[TriggerWordManager] 保存配置文件失败: {e}")


def get_trigger_word(lora_name: str) -> str:
    """获取指定 LoRA 的触发词

    Args:
        lora_name: LoRA 文件名

    Returns:
        str: 触发词内容，未找到返回空字符串
    """
    config = load_trigger_words()
    return config.get(lora_name, "")


def save_trigger_word(lora_name: str, trigger_word: str) -> None:
    """保存或删除单个触发词

    Args:
        lora_name: LoRA 文件名
        trigger_word: 触发词内容（空字符串则删除该条目）
    """
    config = load_trigger_words()

    if trigger_word and trigger_word.strip():
        config[lora_name] = trigger_word.strip()
    else:
        config.pop(lora_name, None)

    save_trigger_words(config)


def get_all_trigger_words() -> list[dict]:
    """获取所有已保存的触发词（排序列表格式）

    Returns:
        list: 触发词列表，每项为 {lora_name, trigger_word}
    """
    config = load_trigger_words()
    return [
        {"lora_name": k, "trigger_word": v}
        for k, v in sorted(config.items(), key=lambda x: x[0].lower())
    ]


def get_lora_list() -> list[str]:
    """获取可用的 LoRA 模型列表

    Returns:
        list: LoRA 文件名列表
    """
    try:
        return folder_paths.get_filename_list("loras")
    except Exception:
        return []
