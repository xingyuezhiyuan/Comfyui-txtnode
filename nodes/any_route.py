import torch

from comfy_api.latest import io

try:
    from comfy_execution.graph_utils import ExecutionBlocker
except Exception:  # 旧版/异常 ComfyUI 降级为 None，保证不崩溃
    ExecutionBlocker = ()

# MASK 去噪阈值：低于 2% 的像素视为不可见残差
MASK_VISIBLE_THRESHOLD = 0.02


class TxtNodeRouteBlocker(io.ComfyNode):
    """是否阻断：按手动开关决定线路数据透传、置空、或静默中断下游。"""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="TxtNodeRouteBlocker",
            display_name="是否阻断",
            category="txtnode",
            description="按开关透传、输出空值或静默阻断一条万能线路。",
            inputs=[
                io.Boolean.Input(
                    "block_switch",
                    display_name="阻断开关",
                    default=False,
                    label_on="阻断",
                    label_off="通过",
                ),
                io.Combo.Input(
                    "block_mode",
                    options=["仅输出空值", "中断后续分支"],
                    display_name="阻断模式",
                    default="仅输出空值",
                ),
                io.AnyType.Input("any", display_name="any", optional=True),
            ],
            outputs=[
                io.AnyType.Output("any", display_name="any"),
            ],
        )

    @classmethod
    def validate_inputs(cls, **kwargs) -> bool:
        # 跳过类型校验，保证未连接/异型输入不报错
        return True

    @classmethod
    def execute(cls, block_switch=False, block_mode="仅输出空值", any=None) -> io.NodeOutput:
        if not block_switch:
            return io.NodeOutput(any)
        # 仅输出空值：下游仍执行，自行处理 None
        if block_mode == "仅输出空值":
            return io.NodeOutput(None)
        # 中断后续分支：把 ExecutionBlocker(None) 作为输出值透传给下游，
        # 实现静默阻断（等同 Ctrl+M 禁用支路，不报错、省算力）。
        if isinstance(ExecutionBlocker, type):
            return io.NodeOutput(ExecutionBlocker(None))
        # 导入失败降级：退化为输出 None
        return io.NodeOutput(None)


class TxtNodeAnyExists(io.ComfyNode):
    """是否存在：检测万能线路有无有效数据，空值时按类型输出占位值并给出布尔结果。"""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="TxtNodeAnyExists",
            display_name="是否存在",
            category="txtnode",
            description="判断万能线路上是否有有效数据，空值时提供类型占位值。",
            inputs=[
                io.AnyType.Input("any", display_name="Any", optional=True),
                # 隐藏 widget：前端 JS 同步检测到的类型，后端据此生成占位值
                io.String.Input(
                    "gh_input_type",
                    default="ANY",
                    optional=True,
                    socketless=True,
                    extra_dict={"hidden": True},
                ),
            ],
            outputs=[
                io.AnyType.Output("any", display_name="Any"),
                io.Boolean.Output("exists", display_name="布尔"),
            ],
        )

    @classmethod
    def validate_inputs(cls, **kwargs) -> bool:
        return True

    @staticmethod
    def _is_black_tensor(value):
        try:
            return hasattr(value, "numel") and value.numel() > 0 and not bool(torch.any(value != 0).item())
        except Exception:
            return False

    @staticmethod
    def _clean_mask_tensor(value):
        """清除肉眼不可见的近黑遮罩残差。"""
        if not torch.is_tensor(value) or value.numel() == 0:
            return value
        return torch.where(value > MASK_VISIBLE_THRESHOLD, value, torch.zeros_like(value))

    @classmethod
    def _is_empty(cls, value, input_type):
        if value is None or (ExecutionBlocker and isinstance(value, ExecutionBlocker)):
            return True
        if input_type == "MASK":
            # 纯黑或仅含不可见低值残差的 MASK 视为空
            return cls._is_black_tensor(value)
        if input_type == "LATENT" and isinstance(value, dict) and "samples" in value:
            return cls._is_black_tensor(value.get("samples"))
        if isinstance(value, str):
            return value == ""
        if isinstance(value, (list, tuple, dict, set)):
            return len(value) == 0
        return False  # 0 和 False 均为有效内容

    @staticmethod
    def _placeholder(input_type):
        t = str(input_type or "ANY").upper()
        if t == "IMAGE":
            return torch.zeros((1, 64, 64, 3), dtype=torch.float32)
        if t == "MASK":
            return torch.zeros((1, 64, 64), dtype=torch.float32)
        if t == "STRING":
            return ""
        if t in ("INT", "INTEGER"):
            return 0
        if t in ("FLOAT", "DOUBLE"):
            return 0.0
        if t == "BOOLEAN":
            return False
        if t == "LATENT":
            return {"samples": torch.zeros((1, 4, 1, 1), dtype=torch.float32)}
        if t in ("CONDITIONING", "CONDITION"):
            return []
        # MODEL / CLIP / VAE 及未知复杂类型不能凭空构造有效对象
        return None

    @staticmethod
    def _runtime_type(value, declared_type):
        t = str(declared_type or "ANY").upper()
        if t not in ("ANY", "*") or value is None:
            return "ANY" if t == "*" else t
        if torch.is_tensor(value):
            if value.ndim >= 4 and value.shape[-1] in (1, 3, 4):
                return "IMAGE"
            if value.ndim in (2, 3):
                return "MASK"
        if isinstance(value, dict) and "samples" in value:
            return "LATENT"
        if isinstance(value, bool):
            return "BOOLEAN"
        if isinstance(value, int):
            return "INT"
        if isinstance(value, float):
            return "FLOAT"
        if isinstance(value, str):
            return "STRING"
        return "ANY"

    @classmethod
    def execute(cls, any=None, gh_input_type="ANY") -> io.NodeOutput:
        input_type = cls._runtime_type(any, gh_input_type)
        if input_type == "MASK":
            # Qwen Image 2.1 RGBA 重载为 MASK 时带 1/255~3/255 alpha 残差，
            # 判空/透传前先清零不可见像素
            any = cls._clean_mask_tensor(any)
        empty = cls._is_empty(any, input_type)
        if not empty:
            return io.NodeOutput(any, True)
        # 空 MASK 保留清理后的原尺寸对象；None 则生成 64x64 黑遮罩
        if input_type == "MASK" and any is not None:
            return io.NodeOutput(any, False)
        if any is None and input_type == "ANY":
            return io.NodeOutput(None, False)
        return io.NodeOutput(cls._placeholder(input_type), False)
