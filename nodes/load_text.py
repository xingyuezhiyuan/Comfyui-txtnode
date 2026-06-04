from comfy_api.latest import io

from .utils import ensure_absolute_path, get_default_output_dir


class LoadTextFilesNode(io.ComfyNode):
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
    def define_schema(cls):
        comfyui_output_dir = get_default_output_dir()
        return io.Schema(
            node_id="LoadTextFilesNode",
            display_name="Load Text Files from Folder",
            category="Utils",
            is_output_node=True,
            inputs=[
                io.String.Input("folder_path", default=comfyui_output_dir),
                io.Int.Input("max_files", default=10, min=1, max=999, step=1, display_mode=io.NumberDisplay.number),
                io.Int.Input("index", default=0, min=0, max=999, step=1, display_mode=io.NumberDisplay.number),
            ],
            outputs=[
                io.String.Output("text"),
                io.String.Output("file_name"),
            ],
        )

    @classmethod
    def execute(cls, folder_path, max_files, index):
        """
        加载指定索引的 txt 文件

        Args:
            folder_path: txt 文件所在的文件夹路径
            max_files: 最大文件数量限制
            index: 要加载的文件索引（从 0 开始）

        Returns:
            NodeOutput: (文件内容，文件名)
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
            return io.NodeOutput(content, selected_file.name)
        except Exception as e:
            print(f"[LoadTextFilesNode] 错误：{str(e)}")
            raise Exception(f"Error loading text file: {str(e)}")
