import folder_paths
from comfy_api.latest import io

from . import trigger_word_manager


class LoRALoaderModelOnly(io.ComfyNode):
    """LoRA 加载器(仅模型) - 加载 LoRA 到模型,不加载到 CLIP

    新增功能:
    - 触发词管理:为每个 LoRA 模型保存自定义触发词
    - 触发词输出:通过输出端口传递触发词到 CLIP 文本编码器
    """

    @classmethod
    def define_schema(cls):
        lora_list = trigger_word_manager.get_lora_list()

        return io.Schema(
            node_id="LoRALoaderModelOnly",
            display_name="LoRA加载器(仅模型)",
            category="loaders/lora",
            inputs=[
                io.Model.Input("model"),
                io.Combo.Input(
                    "lora_name",
                    options=lora_list,
                    default=lora_list[0] if lora_list else "",
                ),
                io.Float.Input(
                    "strength_model",
                    default=1.0,
                    min=-10.0,
                    max=10.0,
                    step=0.01,
                ),
                io.String.Input(
                    "trigger_word",
                    default="",
                    multiline=True,
                    placeholder="输入 LoRA 触发词...",
                ),
                io.String.Input(
                    "upstream_trigger_word",
                    default="",
                    force_input=True,
                    optional=True,
                ),
            ],
            outputs=[
                io.Model.Output("MODEL"),
                io.String.Output("trigger_word"),
            ],
        )

    @classmethod
    def execute(cls, model, lora_name, strength_model, trigger_word, upstream_trigger_word=""):
        """加载 LoRA 模型并返回合并后的触发词

        Args:
            model: 输入模型
            lora_name: LoRA 文件名
            strength_model: 模型强度
            trigger_word: 当前 LoRA 的触发词
            upstream_trigger_word: 上游 LoRA 的触发词(可选)

        Returns:
            NodeOutput: (加载后的模型, 合并后的触发词)
        """
        try:
            import comfy.sd
            import comfy.utils

            # 获取 LoRA 文件路径
            lora_path = folder_paths.get_full_path_or_raise("loras", lora_name)

            # 加载 LoRA 模型
            lora = comfy.utils.load_torch_file(lora_path, safe_load=True)

            # 将 LoRA 应用到模型(不应用到 CLIP)
            model_lora, _ = comfy.sd.load_lora_for_models(model, None, lora, strength_model, 0)

            # 如果提供了触发词,保存到配置文件
            if trigger_word.strip():
                trigger_word_manager.save_trigger_word(lora_name, trigger_word.strip())

            # 合并触发词(上游 + 当前),空值不参与拼接
            parts = []
            if upstream_trigger_word and upstream_trigger_word.strip():
                parts.append(upstream_trigger_word.strip())
            if trigger_word and trigger_word.strip():
                parts.append(trigger_word.strip())

            # 使用 ", " 连接,如果没有触发词则返回空字符串
            merged_trigger_word = ", ".join(parts) if parts else ""

            return io.NodeOutput(model_lora, merged_trigger_word)

        except Exception as e:
            print(f"[LoRALoaderModelOnly] 加载 LoRA 失败: {e}")
            # 加载失败时返回原始模型和合并后的触发词
            parts = []
            if upstream_trigger_word and upstream_trigger_word.strip():
                parts.append(upstream_trigger_word.strip())
            if trigger_word and trigger_word.strip():
                parts.append(trigger_word.strip())
            merged_trigger_word = ", ".join(parts) if parts else ""
            return io.NodeOutput(model, merged_trigger_word)
