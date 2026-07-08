import json
import folder_paths
from comfy_api.latest import io

from .. import trigger_word_manager


class LoRAPromptEncoder(io.ComfyNode):
    """LoRA 提示词编码器 - 集成 LoRA 选择、提示词编辑和 CLIP 文本编码

    功能特点:
    - 多选 LoRA 缩略图网格（支持搜索、分页、文件夹筛选）
    - 点击缩略图自动应用触发词到提示词
    - 每个 LoRA 独立强度控制
    - 内置正面/负面提示词 textarea
    - 自动完成 CLIP 文本编码，输出 CONDITIONING
    """

    @classmethod
    def define_schema(cls):
        lora_list = trigger_word_manager.get_lora_list()

        return io.Schema(
            node_id="LoRAPromptEncoder",
            display_name="LoRA提示词编码器",
            category="loaders/lora",
            inputs=[
                io.Model.Input("model"),
                io.Clip.Input("clip"),
                # 隐藏 widget：存储已选 LoRA 的 JSON 数组
                # 格式: [{"name":"xxx.safetensors","strength":1.0}, ...]
                io.String.Input(
                    "selected_loras",
                    default="[]",
                    optional=True,
                    socketless=True,
                    extra_dict={"hidden": True},
                ),
                # 隐藏 widget：存储 DOM textarea 的正面提示词内容
                io.String.Input(
                    "positive_prompt_dom",
                    default="",
                    optional=True,
                    socketless=True,
                    extra_dict={"hidden": True},
                ),
                # 隐藏 widget：存储 DOM textarea 的负面提示词内容
                io.String.Input(
                    "negative_prompt_dom",
                    default="",
                    optional=True,
                    socketless=True,
                    extra_dict={"hidden": True},
                ),
                # 正面提示词输入端口（可接文本节点）
                io.String.Input(
                    "positive_prompt",
                    default="",
                    optional=True,
                    force_input=True,
                ),
                # 负面提示词输入端口（可接文本节点）
                io.String.Input(
                    "negative_prompt",
                    default="",
                    optional=True,
                    force_input=True,
                ),
            ],
            outputs=[
                io.Model.Output("MODEL"),
                io.Clip.Output("CLIP"),
                io.Conditioning.Output("CONDITIONING"),
                io.Conditioning.Output("NEGATIVE_CONDITIONING"),
            ],
        )

    @classmethod
    def execute(cls, model, clip, selected_loras="[]", positive_prompt="", negative_prompt="",
                positive_prompt_dom="", negative_prompt_dom="", **kwargs):
        """加载多个 LoRA 并编码提示词

        Args:
            model: 输入模型
            clip: 输入 CLIP
            selected_loras: JSON 字符串，已选 LoRA 列表
            positive_prompt: 正面提示词（来自输入端口）
            negative_prompt: 负面提示词（来自输入端口）
            positive_prompt_dom: 正面提示词（来自 DOM textarea）
            negative_prompt_dom: 负面提示词（来自 DOM textarea）

        Returns:
            NodeOutput: (加载后的模型, 加载后的CLIP, 正面条件, 负面条件)
        """
        try:
            import comfy.sd
            import comfy.utils
            import comfy.model_management

            # 合并提示词：端口输入 + DOM textarea 输入（并联）
            def merge_prompts(port_value, dom_value):
                parts = []
                if port_value and port_value.strip():
                    parts.append(port_value.strip())
                if dom_value and dom_value.strip():
                    parts.append(dom_value.strip())
                return ", ".join(parts) if parts else ""

            positive_prompt = merge_prompts(positive_prompt, positive_prompt_dom)
            negative_prompt = merge_prompts(negative_prompt, negative_prompt_dom)

            # 解析已选 LoRA 列表
            try:
                lora_configs = json.loads(selected_loras) if selected_loras else []
            except json.JSONDecodeError:
                lora_configs = []

            # 循环加载并应用每个 LoRA
            current_model = model
            current_clip = clip

            for lora_config in lora_configs:
                lora_name = lora_config.get("name", "")
                strength = lora_config.get("strength", 1.0)

                if not lora_name:
                    continue

                try:
                    # 获取 LoRA 文件路径
                    lora_path = folder_paths.get_full_path_or_raise("loras", lora_name)

                    # 加载 LoRA 模型
                    lora = comfy.utils.load_torch_file(lora_path, safe_load=True)

                    # 将 LoRA 应用到模型和 CLIP（strength_model 和 strength_clip 使用相同值）
                    current_model, current_clip = comfy.sd.load_lora_for_models(
                        current_model, current_clip, lora, strength, strength
                    )
                except Exception as e:
                    print(f"[LoRAPromptEncoder] 加载 LoRA '{lora_name}' 失败: {e}")
                    continue

            # 编码正面提示词
            if positive_prompt and positive_prompt.strip():
                positive_conditioning = current_clip.encode_from_tokens_scheduled(current_clip.tokenize(positive_prompt))
            else:
                positive_conditioning = [[comfy.model_management.get_torch_device(), {}]]

            # 编码负面提示词
            if negative_prompt and negative_prompt.strip():
                negative_conditioning = current_clip.encode_from_tokens_scheduled(current_clip.tokenize(negative_prompt))
            else:
                negative_conditioning = [[comfy.model_management.get_torch_device(), {}]]

            return io.NodeOutput(current_model, current_clip, positive_conditioning, negative_conditioning)

        except Exception as e:
            print(f"[LoRAPromptEncoder] 执行失败: {e}")
            # 失败时返回原始输入和空条件
            import comfy.model_management
            empty_cond = [[comfy.model_management.get_torch_device(), {}]]
            return io.NodeOutput(model, clip, empty_cond, empty_cond)
