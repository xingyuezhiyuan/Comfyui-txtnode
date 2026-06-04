from comfy_api.latest import io

from .utils import ensure_absolute_path, ensure_parent_directory, get_default_output_dir


class SaveStringToTextNode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        comfyui_output_dir = get_default_output_dir()
        return io.Schema(
            node_id="SaveStringToTextNode",
            display_name="Save String to Text File",
            category="Utils",
            is_output_node=True,
            inputs=[
                io.String.Input("text", multiline=True, force_input=True),
                io.String.Input("file_name", default="output"),
                io.String.Input("extension", default="txt"),
                io.Combo.Input("encoding", options=["utf-8", "gbk", "utf-16", "ascii"], default="utf-8"),
                io.Combo.Input("save_mode", options=["single_file", "multiple_files"], default="single_file"),
                io.String.Input("directory_path", default=comfyui_output_dir, optional=True),
            ],
            outputs=[
                io.String.Output("file_path"),
            ],
        )

    @classmethod
    def execute(cls, text, file_name, extension="txt", encoding="utf-8", save_mode="single_file", directory_path=""):
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

                return io.NodeOutput(str(abs_path))
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
                return io.NodeOutput(saved_paths[0])
        except Exception as e:
            raise Exception(f"Error saving file: {str(e)}")
