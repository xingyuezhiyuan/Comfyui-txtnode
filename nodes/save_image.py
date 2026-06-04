import torch
from PIL import Image
import numpy as np
from comfy_api.latest import io

from .utils import ensure_absolute_path, get_default_output_dir


class SaveImageToFolderNode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        comfyui_output_dir = get_default_output_dir()
        return io.Schema(
            node_id="SaveImageToFolderNode",
            display_name="Save Image to Folder",
            category="Utils",
            is_output_node=True,
            inputs=[
                io.Image.Input("images"),
                io.String.Input("file_name", default=""),
                io.Combo.Input("image_format", options=["png", "jpg", "jpeg", "webp"], default="png"),
                io.String.Input("output_folder", default=comfyui_output_dir, optional=True),
            ],
            outputs=[
                io.String.Output("folder_path"),
            ],
        )

    @classmethod
    def execute(cls, images, file_name="", image_format="png", output_folder=""):
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

            return io.NodeOutput(str(output_folder))
        except Exception as e:
            raise Exception(f"Error saving images: {str(e)}")
