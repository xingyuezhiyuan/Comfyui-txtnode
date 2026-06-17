/**
 * 模型预览图管理器
 * 
 * 功能：右键 TW 按钮打开弹窗，管理工作流中所有模型的预览图
 * 支持类型：checkpoints、loras、unet（含 diffusion_models fallback）
 */

import { app } from "../../../scripts/app.js";

// 支持的模型加载器节点类型及其对应的 folder_type
const MODEL_LOADER_NODES = {
    "CheckpointLoaderSimple": "checkpoints",
    "LoraLoader": "loras",
    "LoraLoaderModelOnly": "loras",
    "LoRALoaderModelOnly": "loras",
    "UNETLoader": "unet",
    "UnetLoader": "unet",
    "DiffusionModelLoader": "unet",
};

// 模型类型显示名称
const FOLDER_TYPE_LABELS = {
    "checkpoints": "Checkpoint",
    "loras": "LoRA",
    "unet": "UNet",
};

/**
 * 扫描工作流，获取所有模型加载器及其选择的模型
 * @returns {Array<{folder_type: string, filename: string, node_type: string}>}
 */
function getWorkflowModels() {
    const models = [];
    const seen = new Set(); // 去重（同一模型可能被多个节点加载）
    
    if (!app.graph) return models;
    
    for (const node of app.graph._nodes) {
        const folderType = MODEL_LOADER_NODES[node.type];
        if (!folderType) continue;
        
        // 获取模型文件名（通常是第一个 widget 的值）
        const modelWidget = node.widgets?.find(w => 
            w.name === "ckpt_name" || 
            w.name === "lora_name" || 
            w.name === "unet_name" ||
            w.name === "model_name"
        );
        
        if (!modelWidget?.value) continue;
        
        const filename = modelWidget.value;
        const key = `${folderType}:${filename}`;
        
        if (seen.has(key)) continue;
        seen.add(key);
        
        models.push({
            folder_type: folderType,
            filename: filename,
            node_type: node.type,
        });
    }
    
    return models;
}

/**
 * 检查模型是否有预览图
 * @param {string} folderType - 模型类型
 * @param {string} filename - 模型文件名
 * @returns {Promise<{has_preview: boolean, preview_url: string}>}
 */
async function checkPreviewImage(folderType, filename) {
    const url = `/model_preview/get_image_by_name?folder_type=${folderType}&filename=${encodeURIComponent(filename)}&_t=${Date.now()}`;
    
    try {
        const response = await fetch(url, { method: "HEAD" });
        if (response.ok) {
            return { has_preview: true, preview_url: url };
        }
    } catch (e) {
        // 忽略错误
    }
    
    return { has_preview: false, preview_url: "" };
}

/**
 * 上传预览图（JSON + base64）
 * @param {string} folderType - 模型类型
 * @param {string} filename - 模型文件名
 * @param {File} imageFile - 图片文件
 * @returns {Promise<{success: boolean, message: string}>}
 */
async function uploadPreviewImage(folderType, filename, imageFile) {
    // 将文件转换为 base64
    const imageBase64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            // 去掉 data:image/xxx;base64, 前缀
            const base64 = reader.result.split(",")[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(imageFile);
    });
    
    // 获取文件扩展名
    const imageExt = "." + imageFile.name.split(".").pop().toLowerCase();
    
    try {
        const response = await fetch("/model_preview/upload_preview_image", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                folder_type: folderType,
                filename: filename,
                image_base64: imageBase64,
                image_ext: imageExt,
            }),
        });
        
        if (response.ok) {
            const result = await response.json();
            return { success: true, message: result.message || "预览图已保存" };
        } else {
            const error = await response.text();
            return { success: false, message: `上传失败: ${error}` };
        }
    } catch (e) {
        return { success: false, message: `上传出错: ${e.message}` };
    }
}

/**
 * 获取短文件名
 */
function getShortName(name) {
    return name.includes("\\") ? name.split("\\").pop() : name.includes("/") ? name.split("/").pop() : name;
}

/**
 * 显示上传确认弹窗
 * @param {object} model - 模型信息
 * @param {File} file - 选择的图片文件
 * @param {Function} onConfirm - 确认回调
 */
function showUploadConfirmDialog(model, file, onConfirm) {
    // 移除已存在的弹窗
    document.querySelector(".mp-upload-overlay")?.remove();
    
    const overlay = document.createElement("div");
    overlay.className = "mp-upload-overlay";
    overlay.style.cssText = "position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;";
    
    const dialog = document.createElement("div");
    dialog.style.cssText = "background:#2a2a2e;border:1px solid #555;border-radius:8px;min-width:320px;max-width:400px;display:flex;flex-direction:column;box-shadow:0 8px 32px rgba(0,0,0,0.5);";
    
    // 头部
    const header = document.createElement("div");
    header.style.cssText = "display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid #444;font-size:14px;font-weight:600;color:#e0e0e0;";
    header.innerHTML = `<span>确认上传预览图</span><button style="background:none;border:none;color:#999;cursor:pointer;font-size:16px;padding:0 4px;">✕</button>`;
    header.querySelector("button").onclick = () => overlay.remove();
    dialog.appendChild(header);
    
    // 内容
    const body = document.createElement("div");
    body.style.cssText = "padding:16px;display:flex;flex-direction:column;align-items:center;gap:12px;";
    
    // 图片预览
    const imgPreview = document.createElement("img");
    imgPreview.src = URL.createObjectURL(file);
    imgPreview.style.cssText = "max-width:280px;max-height:200px;border-radius:4px;border:1px solid #444;object-fit:contain;";
    body.appendChild(imgPreview);
    
    // 模型信息
    const info = document.createElement("div");
    info.style.cssText = "text-align:center;font-size:12px;color:#aaa;";
    info.innerHTML = `
        <div style="margin-bottom:4px;">模型: <span style="color:#fff;">${getShortName(model.filename)}</span></div>
        <div>类型: <span style="color:#fff;">${FOLDER_TYPE_LABELS[model.folder_type]}</span></div>
    `;
    body.appendChild(info);
    
    // 按钮
    const btnRow = document.createElement("div");
    btnRow.style.cssText = "display:flex;gap:10px;margin-top:8px;";
    
    const cancelBtn = document.createElement("button");
    cancelBtn.textContent = "取消";
    cancelBtn.style.cssText = "background:#3a3a3e;border:1px solid #555;border-radius:4px;padding:8px 20px;color:#ccc;font-size:13px;cursor:pointer;";
    cancelBtn.onmouseenter = () => cancelBtn.style.background = "#4a4a4e";
    cancelBtn.onmouseleave = () => cancelBtn.style.background = "#3a3a3e";
    cancelBtn.onclick = () => overlay.remove();
    
    const confirmBtn = document.createElement("button");
    confirmBtn.textContent = "确认上传";
    confirmBtn.style.cssText = "background:#4a6ab0;border:none;border-radius:4px;padding:8px 20px;color:#fff;font-size:13px;cursor:pointer;";
    confirmBtn.onmouseenter = () => confirmBtn.style.background = "#5a7ac0";
    confirmBtn.onmouseleave = () => confirmBtn.style.background = "#4a6ab0";
    confirmBtn.onclick = async () => {
        confirmBtn.textContent = "上传中...";
        confirmBtn.disabled = true;
        confirmBtn.style.opacity = "0.6";
        
        const result = await uploadPreviewImage(model.folder_type, model.filename, file);
        
        if (result.success) {
            app.extensionManager.toast.add({
                severity: "success",
                summary: "预览图上传",
                detail: result.message,
                life: 2000,
            });
            overlay.remove();
            onConfirm();
        } else {
            app.extensionManager.toast.add({
                severity: "error",
                summary: "上传失败",
                detail: result.message,
                life: 3000,
            });
            confirmBtn.textContent = "确认上传";
            confirmBtn.disabled = false;
            confirmBtn.style.opacity = "1";
        }
    };
    
    btnRow.appendChild(cancelBtn);
    btnRow.appendChild(confirmBtn);
    body.appendChild(btnRow);
    dialog.appendChild(body);
    
    overlay.appendChild(dialog);
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    document.body.appendChild(overlay);
}

/**
 * 触发文件选择
 * @param {object} model - 模型信息
 * @param {Function} onFileSelected - 文件选择回调
 */
function triggerFileSelect(model, onFileSelected) {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/png,image/jpeg,image/webp";
    input.onchange = () => {
        const file = input.files[0];
        if (file) {
            onFileSelected(file);
        }
    };
    input.click();
}

/**
 * 显示模型预览图管理弹窗
 * @param {MouseEvent} event - 鼠标事件（用于定位弹窗）
 */
export async function showPreviewManager(event) {
    // 移除已存在的弹窗
    document.querySelector(".mp-manager-overlay")?.remove();
    
    // 扫描工作流中的模型
    const models = getWorkflowModels();
    
    // 创建弹窗（与选择触发词弹窗风格一致）
    const overlay = document.createElement("div");
    overlay.className = "mp-manager-overlay";
    overlay.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.3);";
    
    const popup = document.createElement("div");
    popup.style.cssText = "position:fixed;background:#2a2a2e;border:1px solid #555;border-radius:8px;min-width:400px;max-width:520px;max-height:75vh;display:flex;flex-direction:column;box-shadow:0 8px 32px rgba(0,0,0,0.5);";
    
    // 根据鼠标位置计算弹窗位置
    if (event) {
        const popupWidth = 420;
        const popupHeight = 400; // 预估高度
        let left = event.clientX + 10;
        let top = event.clientY - 20;
        
        // 边界检测
        if (left + popupWidth > window.innerWidth) {
            left = window.innerWidth - popupWidth - 20;
        }
        if (top + popupHeight > window.innerHeight) {
            top = window.innerHeight - popupHeight - 20;
        }
        if (left < 10) left = 10;
        if (top < 10) top = 10;
        
        popup.style.left = `${left}px`;
        popup.style.top = `${top}px`;
    } else {
        // 没有鼠标事件时居中显示
        popup.style.cssText += ";left:50%;top:50%;transform:translate(-50%,-50%);";
    }
    
    // 头部（与选择触发词弹窗一致）
    const header = document.createElement("div");
    header.style.cssText = "display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid #444;font-size:14px;font-weight:600;color:#e0e0e0;";
    header.innerHTML = `<span>模型预览图管理</span><button style="background:none;border:none;color:#999;cursor:pointer;font-size:16px;padding:0 4px;">✕</button>`;
    header.querySelector("button").onclick = () => overlay.remove();
    popup.appendChild(header);
    
    // 内容区（与选择触发词弹窗一致）
    const listContainer = document.createElement("div");
    listContainer.style.cssText = "overflow-y:auto;padding:8px;flex:1;";
    
    if (models.length === 0) {
        listContainer.innerHTML = `
            <div style="padding:24px;text-align:center;color:#888;font-size:13px;">
                工作流中未检测到模型加载器节点<br>
                <span style="font-size:11px;color:#666;">支持的节点: CheckpointLoaderSimple, LoraLoader, UNETLoader 等</span>
            </div>
        `;
    } else {
        // 提示
        const tip = document.createElement("div");
        tip.style.cssText = "padding:0 4px 12px;font-size:11px;color:#888;";
        tip.textContent = `检测到 ${models.length} 个模型，点击按钮管理预览图`;
        listContainer.appendChild(tip);
        
        // 渲染每个模型
        for (const model of models) {
            const row = document.createElement("div");
            row.style.cssText = "display:flex;align-items:center;padding:10px;margin:4px 0;border-radius:6px;background:#1e1e22;gap:12px;";
            
            // 缩略图占位
            const thumbContainer = document.createElement("div");
            thumbContainer.style.cssText = "width:60px;height:60px;border-radius:4px;background:#333;display:flex;align-items:center;justify-content:center;overflow:hidden;flex-shrink:0;";
            
            const thumbImg = document.createElement("img");
            thumbImg.style.cssText = "width:100%;height:100%;object-fit:cover;";
            thumbContainer.appendChild(thumbImg);
            
            // 先检查是否有预览图
            const previewCheck = await checkPreviewImage(model.folder_type, model.filename);
            
            if (previewCheck.has_preview) {
                thumbImg.src = previewCheck.preview_url;
                thumbImg.onerror = () => {
                    thumbContainer.innerHTML = `<span style="font-size:10px;color:#666;">无图</span>`;
                };
            } else {
                thumbContainer.innerHTML = `<span style="font-size:10px;color:#666;">无图</span>`;
            }
            
            row.appendChild(thumbContainer);
            
            // 模型信息
            const info = document.createElement("div");
            info.style.cssText = "flex:1;min-width:0;";
            
            const nameDiv = document.createElement("div");
            nameDiv.style.cssText = "font-size:13px;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;";
            nameDiv.textContent = getShortName(model.filename);
            nameDiv.title = model.filename;
            info.appendChild(nameDiv);
            
            const typeDiv = document.createElement("div");
            typeDiv.style.cssText = "font-size:11px;color:#888;margin-top:2px;";
            typeDiv.textContent = FOLDER_TYPE_LABELS[model.folder_type];
            info.appendChild(typeDiv);
            
            row.appendChild(info);
            
            // 操作按钮
            const btn = document.createElement("button");
            btn.style.cssText = "background:#4a6ab0;border:none;border-radius:4px;padding:6px 14px;color:#fff;font-size:12px;cursor:pointer;white-space:nowrap;flex-shrink:0;";
            btn.onmouseenter = () => btn.style.background = "#5a7ac0";
            btn.onmouseleave = () => btn.style.background = "#4a6ab0";
            
            if (previewCheck.has_preview) {
                btn.textContent = "修改";
            } else {
                btn.textContent = "增加";
                btn.style.background = "#3a7a3a";
                btn.onmouseenter = () => btn.style.background = "#4a8a4a";
                btn.onmouseleave = () => btn.style.background = "#3a7a3a";
            }
            
            btn.onclick = () => {
                triggerFileSelect(model, (file) => {
                    showUploadConfirmDialog(model, file, () => {
                        // 上传成功后刷新弹窗
                        overlay.remove();
                        showPreviewManager();
                    });
                });
            };
            
            row.appendChild(btn);
            listContainer.appendChild(row);
        }
    }
    
    popup.appendChild(listContainer);
    
    // 底部
    const footer = document.createElement("div");
    footer.style.cssText = "padding:10px 16px;border-top:1px solid #444;font-size:11px;color:#777;text-align:center;";
    footer.textContent = "预览图将与模型文件同名保存在同一目录";
    popup.appendChild(footer);
    
    overlay.appendChild(popup);
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    document.body.appendChild(overlay);
}
