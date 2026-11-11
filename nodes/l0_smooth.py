import torch
import comfy.model_management as model_management
from comfy_api.latest import io


class L0SmoothNode(io.ComfyNode):
    """L0 梯度最小化平滑：压平平坦色块里的小起伏，保留线条与色块边缘，不生成新细节"""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="L0SmoothNode",
            display_name="L0 平滑去鳞纹",
            category="txtnode",
            inputs=[
                io.Image.Input("image"),
                io.Float.Input("lam", default=0.001, min=0.0, max=0.02, step=0.0001),
            ],
            outputs=[
                io.Image.Output("image"),
            ],
        )

    @classmethod
    def execute(cls, image, lam):
        # lam 为 0 时跳过平滑，原图直通
        if lam <= 0:
            return io.NodeOutput(image)

        device = model_management.get_torch_device()
        outs = []
        for im in image:  # H, W, C，取值 [0, 1]
            S = im.permute(2, 0, 1).to(device=device, dtype=torch.float32)  # 3, H, W
            _, H, W = S.shape
            # 前向差分算子的频域形式，整个迭代过程中只算一次
            fx = torch.zeros(H, W, device=device)
            fy = torch.zeros(H, W, device=device)
            fx[0, 0], fx[0, -1] = -1, 1
            fy[0, 0], fy[-1, 0] = -1, 1
            otf = torch.fft.fft2(fx).abs() ** 2 + torch.fft.fft2(fy).abs() ** 2
            N1 = torch.fft.fft2(S)
            # beta 倍增的惩罚参数：越大越接近目标函数，直到 1e5 停止
            beta = 2 * lam
            while beta < 1e5:
                h = torch.roll(S, -1, 2) - S
                v = torch.roll(S, -1, 1) - S
                # 梯度平方和小于阈值的像素视为平坦区，把该处梯度直接置零
                t = (h ** 2 + v ** 2).sum(0, keepdim=True) < lam / beta
                h = h.masked_fill(t, 0)
                v = v.masked_fill(t, 0)
                div = (torch.roll(h, 1, 2) - h) + (torch.roll(v, 1, 1) - v)
                S = torch.fft.ifft2((N1 + beta * torch.fft.fft2(div)) / (1 + beta * otf)).real
                beta *= 2.0
            outs.append(S.clamp_(0, 1).permute(1, 2, 0))

        return io.NodeOutput(torch.stack(outs).cpu().to(image.dtype))
