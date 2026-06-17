/**
 * 模型预览图悬停显示功能
 * 
 * 功能：右键菜单悬停模型名时，显示同名预览图
 * 支持类型：checkpoints、loras、unet（含 diffusion_models fallback）
 */

import { app } from "../../../scripts/app.js";

// 配置项：弹窗最大宽度
const PREVIEW_MAX_WIDTH = 350;

app.registerExtension({
    name: "Comfyui-txtnode.ModelPreviewHover",
    
    setup() {
        // 1. 创建全局唯一的预览弹窗元素
        const previewImg = document.createElement("img");
        previewImg.id = "model-preview-hover-popup";
        previewImg.style.position = "fixed";
        previewImg.style.display = "none";
        previewImg.style.zIndex = "9999";
        previewImg.style.border = "2px solid #aaa";
        previewImg.style.borderRadius = "8px";
        previewImg.style.background = "#000";
        previewImg.style.maxWidth = `${PREVIEW_MAX_WIDTH}px`;
        previewImg.style.maxHeight = "500px";
        previewImg.style.objectFit = "contain";
        previewImg.style.pointerEvents = "none"; // 鼠标穿透
        previewImg.style.boxShadow = "5px 5px 15px rgba(0,0,0,0.5)";
        document.body.appendChild(previewImg);

        // 2. 全局安全网：任何鼠标按下时强制隐藏预览图
        document.addEventListener("mousedown", () => {
            previewImg.style.display = "none";
            previewImg.src = "";
        }, true); // useCapture=true 确保最先触发

        // 3. 劫持 LiteGraph.ContextMenu（Monkey Patch）
        const OriginalContextMenu = LiteGraph.ContextMenu;

        LiteGraph.ContextMenu = function (values, options) {
            const menuInstance = new OriginalContextMenu(values, options);

            if (!menuInstance.root) return menuInstance;

            // 获取当前右键点击的节点
            const node = app.graph.getNodeOnPos(
                app.canvas.graph_mouse[0], 
                app.canvas.graph_mouse[1]
            );
            if (!node) return menuInstance;

            // 判断模型类型（支持 checkpoints、loras、unet）
            let folderType = null;
            const nodeTypeLower = node.type.toLowerCase();

            if (nodeTypeLower.includes("checkpoint")) {
                folderType = "checkpoints";
            } else if (nodeTypeLower.includes("lora")) {
                folderType = "loras";
            } else if (nodeTypeLower.includes("unet") || nodeTypeLower.includes("diffusion")) {
                folderType = "unet"; // 后端会自动 fallback 到 diffusion_models
            }

            if (!folderType) return menuInstance;

            // 遍历菜单项绑定悬停事件
            const entries = menuInstance.root.querySelectorAll(".litemenu-entry");
            
            entries.forEach(entry => {
                const modelName = entry.innerText || entry.textContent;
                if (!modelName || !modelName.includes(".")) return;

                // 鼠标进入 → 请求预览图
                entry.addEventListener("mouseenter", (e) => {
                    const src = `/model_preview/get_image_by_name?folder_type=${folderType}&filename=${encodeURIComponent(modelName)}`;
                    previewImg.src = src;
                    previewImg.style.display = "block";
                    
                    // 图片加载完成后计算弹出位置
                    previewImg.onload = () => {
                        const rect = entry.getBoundingClientRect();
                        let left = rect.right + 10; // 默认显示在菜单右侧
                        let top = rect.top;

                        // 边界检测：超出右边界则显示在左侧
                        if (left + previewImg.offsetWidth > window.innerWidth) {
                            left = rect.left - previewImg.offsetWidth - 10;
                        }
                        // 边界检测：超出下边界则上移
                        if (top + previewImg.offsetHeight > window.innerHeight) {
                            top = window.innerHeight - previewImg.offsetHeight - 10;
                        }

                        previewImg.style.left = `${left}px`;
                        previewImg.style.top = `${top}px`;
                    };
                    
                    // 图片加载失败 → 隐藏
                    previewImg.onerror = () => {
                        previewImg.style.display = "none";
                    };
                });

                // 鼠标离开 → 隐藏
                entry.addEventListener("mouseleave", () => {
                    previewImg.style.display = "none";
                });

                // 点击选中 → 立即隐藏（防止菜单关闭后图片残留）
                entry.addEventListener("click", () => {
                    previewImg.style.display = "none";
                    previewImg.src = "";
                });
            });

            return menuInstance;
        };

        // 4. 修复原型链，保证其他代码不受影响
        LiteGraph.ContextMenu.prototype = OriginalContextMenu.prototype;
    }
});
