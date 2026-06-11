from typing_extensions import override
from comfy_api.latest import ComfyExtension, io

WEB_DIRECTORY = "./web"

from .nodes import SaveStringToTextNode, SaveImageToFolderNode, LoadTextFilesNode
from .nodes import ResizeAndPadNode, RemovePadFromImageNode
from .lora_loader_node import LoRALoaderModelOnly
from .lora_loader_full_node import LoRALoaderFull

# 导入 server 模块注册 API 路由(装饰器在模块加载时自动注册)
from . import server


class TxtNodeExtension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            SaveStringToTextNode,
            SaveImageToFolderNode,
            LoadTextFilesNode,
            LoRALoaderModelOnly,
            LoRALoaderFull,
            ResizeAndPadNode,
            RemovePadFromImageNode,
        ]


async def comfy_entrypoint() -> TxtNodeExtension:
    return TxtNodeExtension()


__all__ = ["comfy_entrypoint"]
