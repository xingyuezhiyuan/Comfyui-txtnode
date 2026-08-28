"""
PS Bridge 模块 - ComfyUI 与 Photoshop 之间的图像传输桥梁。

提供两个自定义节点：
- GetImageFromPS: 从 ComfyUI input 目录读取 Photoshop 导出的画布和遮罩
- SendImageToPS: 将 ComfyUI 中的图像发送到 output 目录供 Photoshop 读取
"""

import torch
import numpy as np
import os
import threading
from PIL import Image
from comfy_api.latest import io
from io import BytesIO
import folder_paths
import hashlib
import base64

# 文件哈希缓存（用于 IS_CHANGED 变更检测）
_file_hashes = {}

# Base64 缓存（供 UXP 端 HTTP 回退拉取，按含 client_id 的文件名为键，多用户隔离）
# 通过线程锁保护写入，避免多客户端并发 SendImageToPS 时互清彼此缓存（ADR-0035 收尾）。
_base64_cache = {}  # {filename: base64_string}
_base64_cache_lock = threading.Lock()
# 单客户端最多缓存件数（防极端堆积）
_BASE64_CACHE_PER_CLIENT_MAX = 8

# 固定文件名
CANVAS_FILENAME = "xyps_canvas.png"
MASK_FILENAME = "xyps_mask.png"


def _get_file_hash(filepath):
    """计算文件 MD5 哈希，用于变更检测。文件不存在时返回 None。"""
    if not os.path.isfile(filepath):
        return None
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _is_file_changed(filepath):
    """检测文件是否自上次检查后发生了变化。"""
    global _file_hashes
    new_hash = _get_file_hash(filepath)
    if filepath in _file_hashes:
        if _file_hashes[filepath] == new_hash:
            return False  # 未变化
    _file_hashes[filepath] = new_hash
    return True  # 已变化（或首次检查）


def _get_placeholder_image(width=512, height=512):
    """生成占位图（灰色棋盘格），当画布文件不存在时使用。

    Returns:
        PIL.Image.Image: RGB 模式的占位图
    """
    print(f"[GetImageFromPS] 画布文件不存在，使用占位图 ({width}x{height})")
    img = Image.new("RGB", (width, height), color=(60, 60, 60))
    # 绘制简单的棋盘格图案，便于识别为占位图
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    tile_size = 64
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            if (x // tile_size + y // tile_size) % 2 == 0:
                draw.rectangle(
                    [x, y, x + tile_size - 1, y + tile_size - 1],
                    fill=(80, 80, 80)
                )
    return img


# ======================== 辅助函数 ========================

def tensor_to_pil(tensors):
    """将 ComfyUI IMAGE 张量 [B, H, W, C] 转换为 PIL Image 列表。

    ComfyUI 中的图像张量值域为 [0, 1] 的浮点数。

    Args:
        tensors: torch.Tensor, 形状为 [B, H, W, C]

    Returns:
        list[Image.Image]: PIL Image 对象列表
    """
    print(f"[tensor_to_pil] 输入张量形状: {tensors.shape}")
    pil_images = []
    # 遍历批次中的每一张图像
    for i in range(tensors.shape[0]):
        # 取出单张图像 [H, W, C]，转为 numpy，值域 [0, 255]
        img_np = (tensors[i].cpu().numpy() * 255.0).astype(np.uint8)
        pil_img = Image.fromarray(img_np)
        pil_images.append(pil_img)
    print(f"[tensor_to_pil] 转换完成，共 {len(pil_images)} 张 PIL 图像")
    return pil_images


def pil_to_tensor(pil_images):
    """将 PIL Image 列表转换回 ComfyUI IMAGE 张量 [B, H, W, C]。

    Args:
        pil_images: list[Image.Image], PIL Image 对象列表

    Returns:
        torch.Tensor: 形状为 [B, H, W, C]，值域 [0, 1]
    """
    print(f"[pil_to_tensor] 输入 {len(pil_images)} 张 PIL 图像")
    frames = []
    for pil_img in pil_images:
        # 转为 RGB 模式的 numpy 数组
        pil_img = pil_img.convert("RGB")
        np_frame = np.array(pil_img).astype(np.float32) / 255.0
        frames.append(np_frame)
    # 堆叠为 [B, H, W, C] 张量
    tensor = torch.from_numpy(np.stack(frames))
    print(f"[pil_to_tensor] 输出张量形状: {tensor.shape}")
    return tensor


def load_image_from_input(filename):
    """从 ComfyUI input 目录加载图片文件。

    优先直接在 input 目录查找，若未找到则递归搜索所有子文件夹。

    Args:
        filename: str, 要加载的图片文件名

    Returns:
        Image.Image: 加载的 PIL Image 对象

    Raises:
        FileNotFoundError: 在 input 目录及所有子文件夹中均未找到该文件时抛出
    """
    input_dir = folder_paths.get_input_directory()
    print(f"[load_image_from_input] 查找文件: {filename}")
    print(f"[load_image_from_input] input 目录: {input_dir}")

    # 首先尝试在 input 根目录直接查找
    direct_path = os.path.join(input_dir, filename)
    if os.path.isfile(direct_path):
        print(f"[load_image_from_input] 在根目录找到: {direct_path}")
        return Image.open(direct_path)

    # 若根目录未找到，递归搜索子文件夹
    print(f"[load_image_from_input] 根目录未找到，开始递归搜索子文件夹...")
    files, _ = folder_paths.recursive_search(input_dir)
    for rel_path in files:
        if os.path.basename(rel_path) == filename:
            full_path = os.path.join(input_dir, rel_path)
            print(f"[load_image_from_input] 在子文件夹找到: {full_path}")
            return Image.open(full_path)

    # 未找到文件，抛出异常
    raise FileNotFoundError(
        f"在 input 目录及其子文件夹中未找到文件: {filename}"
    )


# ======================== 保存辅助函数 ========================

def save_images_to_output(images, client_id=""):
    """将 IMAGE 张量保存到 ComfyUI output 目录。

    每张图像保存为 SendImageToPS_ 前缀文件；可传入 client_id 使输出文件名带
    客户端命名空间（多用户隔离），未传则回退固定命名。

    Args:
        images: torch.Tensor, 形状为 [B, H, W, C]，值域 [0, 1]
        client_id: str, 客户端稳定 ID（可选）

    Returns:
        list[str]: 保存的文件名列表
    """
    output_dir = folder_paths.get_output_directory()
    print(f"[save_images_to_output] 输出目录: {output_dir}")

    pil_images = tensor_to_pil(images)
    saved_files = []
    prefix = f"SendImageToPS_{client_id}_" if client_id else "SendImageToPS_"
    for i, pil_img in enumerate(pil_images):
        # 确保为 RGB 或 RGBA 模式
        if pil_img.mode not in ("RGB", "RGBA"):
            pil_img = pil_img.convert("RGB")
        file_name = f"{prefix}{i:05d}_.png"
        file_path = os.path.join(output_dir, file_name)
        pil_img.save(file_path, format="PNG")
        print(f"[save_images_to_output] 已保存: {file_path}")
        saved_files.append(file_name)
    print(f"[save_images_to_output] 保存完毕，共 {len(saved_files)} 张图像")
    return saved_files


def tensor_to_base64(tensor):
    """将单个图像张量 [H, W, C] 转换为 Base64 PNG 字符串。

    参考 comfyui-photoshop 的 ComfyUIToPhotoshop.tensor_to_base64 实现。

    Args:
        tensor: torch.Tensor, 形状为 [H, W, C]，值域 [0, 1]

    Returns:
        str: Base64 编码的 PNG 图像字符串
    """
    img_np = (tensor.cpu().numpy() * 255.0).astype(np.uint8)
    pil_img = Image.fromarray(img_np)
    buffer = BytesIO()
    pil_img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _notify_uxp_clients(saved_filenames):
    """通过内部 HTTP 通知 Comfyui-txtnode 后端，后端再通过 WebSocket 广播轻量通知。

    UXP 插件收到通知后主动通过 HTTP GET /view 下载图片，
    仅在 HTTP 下载失败时才回退到 /txtnode/get_image_base64 拉取 Base64 数据。

    Args:
        saved_filenames: list[str], 已保存的文件名列表
    """
    import urllib.request
    import json as _json

    if not saved_filenames:
        return

    data = _json.dumps({
        "filenames": saved_filenames,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8188/txtnode/notify_render",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
        print(f"[SendImageToPS] 已通知 UXP 客户端，共 {len(saved_filenames)} 个文件（轻量通知）")
    except Exception as e:
        print(f"[SendImageToPS] 通知 UXP 客户端失败（可能无客户端连接）: {e}")


# ======================== 节点 1: GetImageFromPS ========================

class GetImageFromPS(io.ComfyNode):
    """从 ComfyUI input 目录读取 UXP 插件导出的画布和遮罩。

    支持按任务指定文件名（image_filename / mask_filename），用于局域网多用户隔离；
    为空时回退到固定文件名 xyps_canvas.png / xyps_mask.png（兼容浏览器前端直接运行的旧流程）。
    文件不存在时使用占位图（画布）和全白遮罩（mask）。
    节点背景显示画布+遮罩预览图。
    """

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="GetImageFromPS",
            display_name="从PS获取图像",
            category="PS Bridge",
            inputs=[
                io.String.Input("image_filename", default="", optional=True,
                    display_name="画布文件名(可选，默认xyps_canvas.png)"),
                io.String.Input("mask_filename", default="", optional=True,
                    display_name="遮罩文件名(可选，默认xyps_mask.png)"),
            ],
            outputs=[
                io.Image.Output("image"),
                io.Mask.Output("mask"),
            ],
        )

    @classmethod
    def IS_CHANGED(cls, image_filename="", mask_filename=""):
        """检测画布或遮罩文件是否变化，触发重新执行。

        支持按任务指定文件名：为空时回退到固定文件名。
        """
        input_dir = folder_paths.get_input_directory()
        canvas_path = os.path.join(input_dir, image_filename or CANVAS_FILENAME)
        mask_path = os.path.join(input_dir, mask_filename or MASK_FILENAME)
        canvas_changed = _is_file_changed(canvas_path)
        mask_changed = _is_file_changed(mask_path)
        if canvas_changed or mask_changed:
            return float("NaN")  # 返回 NaN 表示"始终需要重新执行"
        return False

    @classmethod
    def execute(cls, image_filename="", mask_filename=""):
        """执行节点：加载画布和遮罩。

        image_filename / mask_filename 可指定每任务隔离文件（多用户局域网），
        为空时回退到固定文件名 xyps_canvas.png / xyps_mask.png。

        Returns:
            io.NodeOutput: 包含 image_tensor 和 mask_tensor
        """
        print(f"[GetImageFromPS] ====== 开始执行 =====")
        input_dir = folder_paths.get_input_directory()
        canvas_file = image_filename or CANVAS_FILENAME
        mask_file = mask_filename or MASK_FILENAME
        canvas_path = os.path.join(input_dir, canvas_file)
        mask_path = os.path.join(input_dir, mask_file)

        # 1. 加载画布图像（带回退到占位图）
        print(f"[GetImageFromPS] 查找画布: {canvas_path}")
        if os.path.isfile(canvas_path):
            canvas_pil = Image.open(canvas_path)
            print(f"[GetImageFromPS] 画布加载成功: 尺寸={canvas_pil.size}, 模式={canvas_pil.mode}")
        else:
            print(f"[GetImageFromPS] 画布文件不存在，使用占位图")
            canvas_pil = _get_placeholder_image()
            # 将占位图保存到 input 目录，供 ComfyUI 前端 nodestyle.js 加载预览
            try:
                canvas_pil.save(canvas_path, format="PNG")
                print(f"[GetImageFromPS] 占位图画布已保存至: {canvas_path}")
            except Exception as e:
                print(f"[GetImageFromPS] 占位图画布保存失败: {e}")

        # 2. RGB 模式转换
        if canvas_pil.mode != "RGB":
            original_mode = canvas_pil.mode
            canvas_pil = canvas_pil.convert("RGB")
            print(f"[GetImageFromPS] 画布模式转换: {original_mode} -> RGB")

        # 3. 获取画布尺寸（用于遮罩匹配）
        canvas_w, canvas_h = canvas_pil.size

        # 4. 转换为 ComfyUI IMAGE 张量
        print(f"[GetImageFromPS] 正在转换画布为 IMAGE 张量...")
        image_tensor = pil_to_tensor([canvas_pil])
        print(f"[GetImageFromPS] IMAGE 张量形状: {image_tensor.shape}")

        # 5. 处理遮罩
        print(f"[GetImageFromPS] 查找遮罩: {mask_path}")
        if os.path.isfile(mask_path):
            mask_pil = Image.open(mask_path)
            print(f"[GetImageFromPS] 遮罩加载成功: 尺寸={mask_pil.size}, 模式={mask_pil.mode}")
            if mask_pil.mode != "RGB":
                mask_pil = mask_pil.convert("RGB")
            mask_np = np.array(mask_pil).astype(np.float32)
            # 取红色通道作为灰度遮罩，归一化到 [0, 1]
            mask_arr = mask_np[:, :, 0] / 255.0
            print(f"[GetImageFromPS] 遮罩红色通道提取完成，值域: [{mask_arr.min():.4f}, {mask_arr.max():.4f}]")
            # 缩放遮罩至画布尺寸（如果需要）
            if mask_arr.shape[0] != canvas_h or mask_arr.shape[1] != canvas_w:
                print(f"[GetImageFromPS] 遮罩尺寸不匹配，正在缩放...")
                mask_pil_resized = Image.fromarray(
                    (mask_arr * 255.0).astype(np.uint8)
                ).resize((canvas_w, canvas_h), resample=Image.LANCZOS)
                mask_arr = np.array(mask_pil_resized).astype(np.float32) / 255.0
        else:
            print(f"[GetImageFromPS] 遮罩文件不存在，生成全白遮罩")
            mask_arr = np.ones((canvas_h, canvas_w), dtype=np.float32)
            print(f"[GetImageFromPS] 全白遮罩尺寸: {canvas_w}x{canvas_h}")
            # 将全白遮罩保存到 input 目录，供 ComfyUI 前端 nodestyle.js 加载预览
            try:
                white_mask_pil = Image.fromarray(
                    (mask_arr * 255.0).astype(np.uint8), mode="L"
                ).convert("RGB")
                white_mask_pil.save(mask_path, format="PNG")
                print(f"[GetImageFromPS] 全白遮罩已保存至: {mask_path}")
            except Exception as e:
                print(f"[GetImageFromPS] 全白遮罩保存失败: {e}")

        # 6. 转换为 ComfyUI MASK 张量 [1, H, W]
        mask_tensor = torch.from_numpy(mask_arr).unsqueeze(0)
        print(f"[GetImageFromPS] MASK 张量形状: {mask_tensor.shape}")

        print(f"[GetImageFromPS] ====== 执行完毕 =====")
        return io.NodeOutput(image_tensor, mask_tensor)


# ======================== 节点 2: SendImageToPS ========================

class SendImageToPS(io.ComfyNode):
    """将 ComfyUI 中的图像发送到 output 目录，供 Photoshop 读取。

    纯输出节点——不传递图像张量，仅负责保存和通知 UXP 客户端。
    输入:
        - images: ComfyUI IMAGE 张量
    """

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="SendImageToPS",
            display_name="发送图像到PS",
            category="PS Bridge",
            is_output_node=True,
            inputs=[
                io.Image.Input("images"),
                io.String.Input("client_id", default="", optional=True,
                    display_name="客户端ID(可选，用于多用户输出隔离)"),
            ],
            outputs=[],  # 无输出——纯保存+通知节点，不传递图像张量
        )

    @classmethod
    def execute(cls, images, client_id=""):
        """执行节点：保存图像到输出目录，缓存 Base64 数据，并通知 UXP 客户端。

        流程：
        1. 保存 PNG 到 output/ 目录（供 HTTP GET /view 下载；可选按 client_id 隔离命名）
        2. 将 Base64 数据缓存到内存（供 HTTP 下载失败时回退拉取，键为含 client_id 的文件名）
        3. 通过 WebSocket 推送轻量通知（仅包含文件名）

        Args:
            images: torch.Tensor, 形状为 [B, H, W, C]，值域 [0, 1]
            client_id: str, 客户端稳定 ID（可选，用于输出隔离命名与缓存键）
        """
        print(f"[SendImageToPS] ====== 开始执行 ======")
        print(f"[SendImageToPS] images 张量形状: {images.shape}, client_id={client_id or '(未指定，回退固定名)'}")

        # 1. 保存图像到 output 目录
        saved_filenames = save_images_to_output(images, client_id)

        # 2. 缓存 Base64 数据（键为含 client_id 的文件名，多用户隔离）
        #    加锁避免多客户端并发时互清彼此缓存；仅清理本客户端旧键并按客户端保留上限。
        batch_size = min(images.shape[0], 4)
        prefix = f"SendImageToPS_{client_id}_" if client_id else "SendImageToPS_"
        with _base64_cache_lock:
            # 仅移除本客户端前缀的旧键（含固定名前缀），不触碰其他客户端缓存
            for old_key in list(_base64_cache.keys()):
                if old_key.startswith(prefix):
                    del _base64_cache[old_key]
            for i in range(batch_size):
                filename = f"{prefix}{i:05d}_.png"
                _base64_cache[filename] = tensor_to_base64(images[i])
            # 若本客户端缓存仍超上限，LRU 式丢弃最旧（按插入顺序近似）
            own_keys = [k for k in _base64_cache.keys() if k.startswith(prefix)]
            if len(own_keys) > _BASE64_CACHE_PER_CLIENT_MAX:
                for old_key in own_keys[: len(own_keys) - _BASE64_CACHE_PER_CLIENT_MAX]:
                    _base64_cache.pop(old_key, None)
        print(f"[SendImageToPS] Base64 缓存已更新（本客户端 {batch_size} 张，锁定保护）")

        # 3. 通知 UXP 客户端（轻量通知，仅推送文件名）
        _notify_uxp_clients(saved_filenames)

        print(f"[SendImageToPS] ====== 执行完毕 ======")
        return io.NodeOutput()
