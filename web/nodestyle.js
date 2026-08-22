/**
 * PS Bridge 节点样式扩展
 * 在 GetImageFromPS 节点背景上显示画布 + 遮罩预览图。
 * 参考: comfyui-photoshop 插件的 nodestyle.js
 */
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const CANVAS_FILE = "xyps_canvas.png";
const MASK_FILE = "xyps_mask.png";

// 预取图片 URL（与 comfyui-photoshop 相同的模式）
const canvasResponse = await api.fetchApi(`/view?filename=${CANVAS_FILE}&type=input`);
const maskResponse = await api.fetchApi(`/view?filename=${MASK_FILE}&type=input`);

// ========== 图片加载辅助 ==========
function fetchImage(url) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error(`图片加载失败: ${url}`));
        img.src = url;
    });
}

// ========== 设置节点背景（contain 模式） ==========
function setBackgroundImageContain(node, canvasUrl, maskUrl) {
    Promise.all([fetchImage(canvasUrl), fetchImage(maskUrl).catch(() => null)])
        .then(([canvasImg, maskImg]) => {
            const drawImage = () => {
                if (!canvasImg) return;

                const nodeWidth = node.size[0];
                const nodeHeight = node.size[1];
                const margin = 8;
                const drawAreaW = nodeWidth - margin * 2;
                const drawAreaH = nodeHeight - margin * 2 - 20;

                if (drawAreaW <= 0 || drawAreaH <= 0) return;

                const imgAspect = canvasImg.width / canvasImg.height;
                const areaAspect = drawAreaW / drawAreaH;

                let drawW, drawH, drawX, drawY;
                if (imgAspect > areaAspect) {
                    drawW = drawAreaW;
                    drawH = drawAreaW / imgAspect;
                    drawX = margin;
                    drawY = margin + 20 + (drawAreaH - drawH) / 2;
                } else {
                    drawH = drawAreaH;
                    drawW = drawAreaH * imgAspect;
                    drawX = margin + (drawAreaW - drawW) / 2;
                    drawY = margin + 20;
                }

                node.onDrawBackground = function (ctx) {
                    ctx.drawImage(canvasImg, drawX, drawY, drawW, drawH);
                    if (maskImg) {
                        ctx.globalAlpha = 0.65;
                        ctx.globalCompositeOperation = "darken";
                        ctx.drawImage(maskImg, drawX, drawY, drawW, drawH);
                        ctx.globalCompositeOperation = "source-over";
                        ctx.globalAlpha = 1.0;
                    }
                };
                node.setDirtyCanvas(true, true);
            };

            drawImage();
            node.onResize = drawImage;
        })
        .catch((e) => {
            console.log("[PSBridge] 预览图加载失败:", e);
            node.onDrawBackground = null;
            node.setDirtyCanvas(true, true);
        });
}

// ========== 刷新节点预览 ==========
function refreshPreview(node) {
    const ts = Date.now();
    const canvasUrl = `${canvasResponse.url}&t=${ts}`;
    const maskUrl = `${maskResponse.url}&t=${ts}`;
    setBackgroundImageContain(node, canvasUrl, maskUrl);
}

// 收集所有 GetImageFromPS 节点实例
const psNodes = [];

app.registerExtension({
    name: "Comfyui-txtnode.PSBridgeNodeStyle",

    async nodeCreated(node) {
        if (node.comfyClass !== "GetImageFromPS") return;

        psNodes.push(node);
        // 延迟加载，确保节点尺寸已初始化
        setTimeout(() => refreshPreview(node), 500);
    },

    setup() {
        // 工作流执行后自动刷新所有 GetImageFromPS 节点预览
        const refreshAll = () => {
            psNodes.forEach((node) => refreshPreview(node));
        };

        api.addEventListener("execution_start", refreshAll);
        api.addEventListener("executed", refreshAll);
        // UXP 插件上传画布/遮罩后，后端广播此自定义事件触发预览刷新
        // （UXP 通过 HTTP 提交工作流不带 client_id，execution_start 不会送达前端）
        api.addEventListener("txtnode_preview_updated", refreshAll);
    },
});
