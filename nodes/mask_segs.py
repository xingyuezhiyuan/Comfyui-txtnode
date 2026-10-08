import logging

import numpy as np
import torch
import cv2
from collections import namedtuple
from comfy_api.latest import io
from comfy.utils import common_upscale

# 与 Impact Pack 保持一致的最大分辨率常量
MAX_RESOLUTION = 16384

# SEGS 自定义类型：类型名字符串固定为 "SEGS"，与 Impact Pack 生态兼容（见 docs/adr/0001）
SEGSType = io.Custom("SEGS")

# 单个分割条目：局部图像、局部遮罩、置信度、裁剪区域、边界框、标签、控制网包装
SEG = namedtuple(
    "SEG",
    ['cropped_image', 'cropped_mask', 'confidence', 'crop_region', 'bbox', 'label', 'control_net_wrapper'],
    defaults=[None],
)


# ============================================================
# 遮罩/SEGS 核心工具函数（移植自 Impact Pack，行为保持一致）
# ============================================================

def make_2d_mask(mask):
    """将遮罩统一为 2D (h,w) 形状"""
    if len(mask.shape) == 4:
        return mask.squeeze(0).squeeze(0)
    elif len(mask.shape) == 3:
        return mask.squeeze(0)
    return mask


def make_3d_mask(mask):
    """将遮罩统一为 3D (1,h,w) 形状"""
    if len(mask.shape) == 4:
        return mask.squeeze(0)
    elif len(mask.shape) == 2:
        return mask.unsqueeze(0)
    return mask


def normalize_region(limit, startp, size):
    """把裁剪区域起点/终点规整到 [0, limit) 范围内"""
    if startp < 0:
        new_endp = min(limit, size)
        new_startp = 0
    elif startp + size > limit:
        new_startp = max(0, limit - size)
        new_endp = limit
    else:
        new_startp = startp
        new_endp = min(limit, startp + size)

    return int(new_startp), int(new_endp)


def make_crop_region(w, h, bbox, crop_factor, crop_min_size=None):
    """以 bbox 为中心、按 crop_factor 向外扩展，生成裁剪区域 [x1, y1, x2, y2]"""
    x1 = bbox[0]
    y1 = bbox[1]
    x2 = bbox[2]
    y2 = bbox[3]

    bbox_w = x2 - x1
    bbox_h = y2 - y1

    crop_w = bbox_w * crop_factor
    crop_h = bbox_h * crop_factor

    if crop_min_size is not None:
        crop_w = max(crop_min_size, crop_w)
        crop_h = max(crop_min_size, crop_h)

    kernel_x = x1 + bbox_w / 2
    kernel_y = y1 + bbox_h / 2

    new_x1 = int(kernel_x - crop_w / 2)
    new_y1 = int(kernel_y - crop_h / 2)

    # 确保区域在 (w,h) 范围内
    new_x1, new_x2 = normalize_region(w, new_x1, crop_w)
    new_y1, new_y2 = normalize_region(h, new_y1, crop_h)

    return [new_x1, new_y1, new_x2, new_y2]


def mask_to_segs(mask, combined, crop_factor, bbox_fill, drop_size=1, label='A', crop_min_size=None, is_contour=True):
    """将遮罩转换为 SEGS 结构。

    combined=True 时把整个遮罩作为单个 SEG（整体 bbox）；
    combined=False 时用 cv2 轮廓分离，每个独立轮廓生成一个 SEG，
    小于 drop_size 的区域被丢弃；is_contour 决定取轮廓填充还是原遮罩交集。
    """
    drop_size = max(drop_size, 1)
    if mask is None:
        logging.info("[mask_to_segs] 无法运行：MASK 为空。")
        return ([],)

    if isinstance(mask, np.ndarray):
        pass  # mask 已经是 NumPy 数组
    else:
        try:
            mask = mask.numpy()
        except AttributeError:
            logging.info("[mask_to_segs] 无法运行：MASK 不是 NumPy 数组或张量。")
            return ([],)

    result = []

    if len(mask.shape) == 2:
        mask = np.expand_dims(mask, axis=0)

    for i in range(mask.shape[0]):
        mask_i = mask[i]

        if combined:
            # 整体模式：所有非零像素合并为一个 bbox
            indices = np.nonzero(mask_i)
            if len(indices[0]) > 0 and len(indices[1]) > 0:
                bbox = (
                    np.min(indices[1]),
                    np.min(indices[0]),
                    np.max(indices[1]),
                    np.max(indices[0]),
                )
                crop_region = make_crop_region(
                    mask_i.shape[1], mask_i.shape[0], bbox, crop_factor
                )
                x1, y1, x2, y2 = crop_region

                if x2 - x1 > 0 and y2 - y1 > 0:
                    cropped_mask = mask_i[y1:y2, x1:x2]

                    if bbox_fill:
                        bx1, by1, bx2, by2 = bbox
                        cropped_mask = cropped_mask.copy()
                        cropped_mask[by1:by2, bx1:bx2] = 1.0

                    if cropped_mask is not None:
                        item = SEG(None, cropped_mask, 1.0, crop_region, bbox, label, None)
                        result.append(item)

        else:
            # 轮廓分离模式：每个顶层轮廓独立成一个 SEG（跳过子轮廓）
            mask_i_uint8 = (mask_i * 255.0).astype(np.uint8)
            contours, ctree = cv2.findContours(mask_i_uint8, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            for j, contour in enumerate(contours):
                hierarchy = ctree[0][j]
                if hierarchy[3] != -1:
                    continue

                separated_mask = np.zeros_like(mask_i_uint8)
                cv2.drawContours(separated_mask, [contour], 0, 255, -1)
                separated_mask = np.array(separated_mask / 255.0).astype(np.float32)

                x, y, w, h = cv2.boundingRect(contour)
                bbox = x, y, x + w, y + h
                crop_region = make_crop_region(
                    mask_i.shape[1], mask_i.shape[0], bbox, crop_factor, crop_min_size
                )

                if w > drop_size and h > drop_size:
                    if is_contour:
                        mask_src = separated_mask
                    else:
                        mask_src = mask_i * separated_mask

                    cropped_mask = np.array(
                        mask_src[
                            crop_region[1]: crop_region[3],
                            crop_region[0]: crop_region[2],
                        ]
                    )

                    if bbox_fill:
                        cx1, cy1, _, _ = crop_region
                        bx1 = x - cx1
                        bx2 = x + w - cx1
                        by1 = y - cy1
                        by2 = y + h - cy1
                        cropped_mask[by1:by2, bx1:bx2] = 1.0

                    if cropped_mask is not None:
                        cropped_mask = torch.clip(torch.from_numpy(cropped_mask), 0, 1.0)
                        item = SEG(None, cropped_mask.numpy(), 1.0, crop_region, bbox, label, None)
                        result.append(item)

    if not result:
        logging.info("[mask_to_segs] 空遮罩。")

    logging.info(f"检测到的 SEGS 数量: {len(result)}")

    # 形状: (b,h,w) -> (h,w)
    return (mask.shape[1], mask.shape[2]), result


def segs_to_masklist(segs):
    """把 SEGS 中每个 SEG 的局部遮罩按裁剪区域贴回全图，返回遮罩列表"""
    shape = segs[0]
    h = shape[0]
    w = shape[1]

    masks = []
    for seg in segs[1]:
        if isinstance(seg.cropped_mask, np.ndarray):
            cropped_mask = torch.from_numpy(seg.cropped_mask)
        else:
            cropped_mask = seg.cropped_mask

        if cropped_mask.ndim == 2:
            cropped_mask = cropped_mask.unsqueeze(0)

        n = len(cropped_mask)

        mask = torch.zeros((n, h, w), dtype=torch.uint8)
        crop_region = seg.crop_region
        mask[:, crop_region[1]:crop_region[3], crop_region[0]:crop_region[2]] |= (cropped_mask * 255).to(torch.uint8)
        mask = (mask / 255.0).to(torch.float32)

        for x in mask:
            masks.append(x)

    if len(masks) == 0:
        empty_mask = torch.zeros((h, w), dtype=torch.float32, device="cpu")
        masks = [empty_mask]

    return masks


def subtract_masks(mask1, mask2):
    """遮罩相减：整幅逐像素饱和运算 mask1 - mask2；形状不一致时容错返回 mask1"""
    mask1 = mask1.cpu()
    mask2 = mask2.cpu()
    cv2_mask1 = np.array(mask1) * 255
    cv2_mask2 = np.array(mask2) * 255

    if cv2_mask1.shape == cv2_mask2.shape:
        cv2_mask = cv2.subtract(cv2_mask1, cv2_mask2)
        return torch.clamp(torch.from_numpy(cv2_mask) / 255.0, min=0, max=1)
    else:
        # 形状不兼容时不做处理——多为空遮罩，容错返回 mask1
        return mask1


def add_masks(mask1, mask2):
    """遮罩相加：整幅逐像素饱和运算 mask1 + mask2；形状不一致时容错返回 mask1"""
    mask1 = mask1.cpu()
    mask2 = mask2.cpu()
    cv2_mask1 = np.array(mask1) * 255
    cv2_mask2 = np.array(mask2) * 255

    if cv2_mask1.shape == cv2_mask2.shape:
        cv2_mask = cv2.add(cv2_mask1, cv2_mask2)
        return torch.clamp(torch.from_numpy(cv2_mask) / 255.0, min=0, max=1)
    else:
        # 形状不兼容时不做处理——多为空遮罩，容错返回 mask1
        return mask1


# ============================================================
# MaskListToMaskBatchNode — 遮罩列表到遮罩
# ============================================================

class MaskListToMaskBatchNode(io.ComfyNode):
    """把 MASK 列表合并为一个 MASK 批量；尺寸不一致时以第一个遮罩为基准用 lanczos 居中缩放"""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MaskListToMaskBatchNode",
            display_name="遮罩列表到遮罩",
            category="txtnode",
            is_input_list=True,
            inputs=[
                io.Mask.Input("mask"),
            ],
            outputs=[
                io.Mask.Output("mask"),
            ],
        )

    @classmethod
    def execute(cls, mask):
        # 空列表：返回 64x64 空遮罩（与 Impact 原节点行为一致）
        if len(mask) == 0:
            empty_mask = torch.zeros((1, 64, 64), dtype=torch.float32, device="cpu").unsqueeze(0)
            return io.NodeOutput(empty_mask,)

        masks_3d = [make_3d_mask(m) for m in mask]
        target_shape = masks_3d[0].shape[1:]
        upscaled_masks = []
        for m in masks_3d:
            # 尺寸不一致时复制为 3 通道后用 lanczos 居中缩放到基准尺寸（与 Impact 原节点一致）
            if m.shape[1:] != target_shape:
                m = m.unsqueeze(1).repeat(1, 3, 1, 1)
                m = common_upscale(m, target_shape[1], target_shape[0], "lanczos", "center")
                m = m[:, 0, :, :]

            upscaled_masks.append(m)

        result = torch.cat(upscaled_masks, dim=0)
        return io.NodeOutput(result,)


# ============================================================
# MaskToSEGSNode — 遮罩到Seg
# ============================================================

class MaskToSEGSNode(io.ComfyNode):
    """把遮罩转换为 SEGS：合并模式取整体 bbox，否则按轮廓分离成多个 SEG"""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MaskToSEGSNode",
            display_name="遮罩到Seg",
            category="txtnode",
            inputs=[
                io.Mask.Input("mask"),
                io.Boolean.Input("combined", default=False, label_on="True", label_off="False"),
                io.Float.Input("crop_factor", default=3.0, min=1.0, max=100, step=0.1),
                io.Boolean.Input("bbox_fill", default=False, label_on="enabled", label_off="disabled"),
                io.Int.Input("drop_size", default=10, min=1, max=MAX_RESOLUTION, step=1),
                io.Boolean.Input("contour_fill", default=False, label_on="enabled", label_off="disabled"),
            ],
            outputs=[
                SEGSType.Output("segs"),
            ],
        )

    @classmethod
    def execute(cls, mask, combined, crop_factor, bbox_fill, drop_size, contour_fill=False):
        mask = make_2d_mask(mask)
        result = mask_to_segs(mask, combined, crop_factor, bbox_fill, drop_size, is_contour=contour_fill)
        return io.NodeOutput(result,)


# ============================================================
# SegsToMaskListNode — Seg到遮罩列表
# ============================================================

class SegsToMaskListNode(io.ComfyNode):
    """把 SEGS 拆回遮罩列表：每个 SEG 的局部遮罩按裁剪区域贴回全图"""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="SegsToMaskListNode",
            display_name="Seg到遮罩列表",
            category="txtnode",
            inputs=[
                SEGSType.Input("segs"),
            ],
            outputs=[
                io.Mask.Output("mask", is_output_list=True),
            ],
        )

    @classmethod
    def execute(cls, segs):
        masks = segs_to_masklist(segs)
        if len(masks) == 0:
            empty_mask = torch.zeros(segs[0], dtype=torch.float32, device="cpu")
            masks = [empty_mask]
        masks = [make_3d_mask(mask) for mask in masks]
        return io.NodeOutput(masks,)


# ============================================================
# SubtractMaskNode — 遮罩相减
# ============================================================

class SubtractMaskNode(io.ComfyNode):
    """两幅遮罩整幅逐像素相减（饱和运算）；尺寸不一致时容错返回遮罩1"""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="SubtractMaskNode",
            display_name="遮罩相减",
            category="txtnode",
            inputs=[
                io.Mask.Input("mask1"),
                io.Mask.Input("mask2"),
            ],
            outputs=[
                io.Mask.Output("mask"),
            ],
        )

    @classmethod
    def execute(cls, mask1, mask2):
        return io.NodeOutput(subtract_masks(mask1, mask2),)


# ============================================================
# AddMaskNode — 遮罩相加
# ============================================================

class AddMaskNode(io.ComfyNode):
    """两幅遮罩整幅逐像素相加（饱和运算）；尺寸不一致时容错返回遮罩1"""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="AddMaskNode",
            display_name="遮罩相加",
            category="txtnode",
            inputs=[
                io.Mask.Input("mask1"),
                io.Mask.Input("mask2"),
            ],
            outputs=[
                io.Mask.Output("mask"),
            ],
        )

    @classmethod
    def execute(cls, mask1, mask2):
        return io.NodeOutput(add_masks(mask1, mask2),)
