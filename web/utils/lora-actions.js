/**
 * LoRA 操作共享工具模块
 *
 * 提供触发词编辑和预览图上传的通用功能，
 * 供 trigger_word_picker.js 和 lora_prompt_encoder.js 共用。
 */

import { app } from "../../../scripts/app.js";
import { saveTriggerWord } from "./trigger-word-api.js";

/**
 * 获取 LoRA 文件名的简短形式
 */
export function getShortName(name) {
    return name.includes("\\") ? name.split("\\").pop() : name.includes("/") ? name.split("/").pop() : name;
}

/**
 * 显示编辑触发词对话框
 * @param {string} loraName - LoRA 文件名
 * @param {string} currentWord - 当前触发词
 * @param {Function} [onSaved] - 保存成功后的回调
 */
export function showEditTriggerWordDialog(loraName, currentWord, onSaved) {
    const short = getShortName(loraName);

    const editOv = document.createElement("div");
    editOv.className = "txtnode-tw-overlay";
    editOv.style.cssText = "position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;";

    const pop = document.createElement("div");
    pop.style.cssText = "background:#2a2a2e;border:1px solid #555;border-radius:8px;min-width:360px;max-width:480px;display:flex;flex-direction:column;box-shadow:0 8px 32px rgba(0,0,0,0.5);";

    // 头部
    const hdr = document.createElement("div");
    hdr.style.cssText = "display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid #444;font-size:14px;font-weight:600;color:#e0e0e0;";
    hdr.innerHTML = `<span>修改触发词</span><button style="background:none;border:none;color:#999;cursor:pointer;font-size:16px;padding:0 4px;"></button>`;
    hdr.querySelector("button").onclick = () => editOv.remove();
    pop.appendChild(hdr);

    // 内容
    const body = document.createElement("div");
    body.style.cssText = "padding:14px;";

    const loraLabel = document.createElement("div");
    loraLabel.style.cssText = "font-size:11px;color:#888;margin-bottom:6px;";
    loraLabel.textContent = short;
    loraLabel.title = loraName;
    body.appendChild(loraLabel);

    const input = document.createElement("textarea");
    input.value = currentWord;
    input.style.cssText = "width:100%;min-height:60px;background:#1a1a1e;border:1px solid #444;border-radius:4px;padding:8px;color:#e0e0e0;font-size:12px;resize:vertical;outline:none;box-sizing:border-box;";
    input.onfocus = () => input.style.borderColor = "#4a6ab0";
    input.onblur = () => input.style.borderColor = "#444";
    body.appendChild(input);

    // 按钮
    const btnRow = document.createElement("div");
    btnRow.style.cssText = "display:flex;justify-content:flex-end;gap:8px;margin-top:12px;";

    const cancelBtn = document.createElement("button");
    cancelBtn.textContent = "取消";
    cancelBtn.style.cssText = "background:#3a3a3e;border:1px solid #555;border-radius:4px;padding:6px 16px;color:#ccc;font-size:12px;cursor:pointer;";
    cancelBtn.onmouseenter = () => cancelBtn.style.background = "#4a4a4e";
    cancelBtn.onmouseleave = () => cancelBtn.style.background = "#3a3a3e";
    cancelBtn.onclick = () => editOv.remove();

    const saveBtn = document.createElement("button");
    saveBtn.textContent = "保存";
    saveBtn.style.cssText = "background:#4a6ab0;border:none;border-radius:4px;padding:6px 16px;color:#fff;font-size:12px;cursor:pointer;";
    saveBtn.onmouseenter = () => saveBtn.style.background = "#5a7ac0";
    saveBtn.onmouseleave = () => saveBtn.style.background = "#4a6ab0";

    saveBtn.onclick = async () => {
        const newWord = input.value.trim();

        saveBtn.textContent = "保存中...";
        saveBtn.disabled = true;
        saveBtn.style.opacity = "0.6";

        const result = await saveTriggerWord(loraName, newWord);
        if (result.success) {
            const message = newWord ? result.message : "已删除触发词";
            app.extensionManager.toast.add({
                severity: "success", summary: "修改触发词", detail: message, life: 2000
            });
            editOv.remove();
            onSaved?.(newWord);
        } else {
            app.extensionManager.toast.add({
                severity: "error", summary: "修改失败", detail: result.message, life: 3000
            });
            saveBtn.textContent = "保存";
            saveBtn.disabled = false;
            saveBtn.style.opacity = "1";
        }
    };

    // 回车键保存
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            saveBtn.click();
        }
    });

    btnRow.appendChild(cancelBtn);
    btnRow.appendChild(saveBtn);
    body.appendChild(btnRow);
    pop.appendChild(body);

    editOv.appendChild(pop);
    editOv.onclick = e => { if (e.target === editOv) editOv.remove(); };
    document.body.appendChild(editOv);

    // 自动聚焦输入框
    setTimeout(() => {
        input.focus();
        input.select();
    }, 100);
}

/**
 * 上传 LoRA 预览图
 * @param {string} loraName - LoRA 文件名
 * @param {Function} [onUploaded] - 上传成功后的回调
 */
export async function uploadLoraPreview(loraName, onUploaded) {
    const short = getShortName(loraName);

    // 触发文件选择
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/png,image/jpeg,image/webp";

    input.onchange = async () => {
        const file = input.files[0];
        if (!file) return;

        // 显示确认弹窗
        const overlay = document.createElement("div");
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
        info.innerHTML = `<div>模型: <span style="color:#fff;">${short}</span></div><div>类型: <span style="color:#fff;">LoRA</span></div>`;
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

            // 将文件转换为 base64
            const imageBase64 = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result.split(",")[1]);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });

            const imageExt = "." + file.name.split(".").pop().toLowerCase();

            try {
                const response = await fetch("/model_preview/upload_preview_image", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        folder_type: "loras",
                        filename: loraName,
                        image_base64: imageBase64,
                        image_ext: imageExt,
                    }),
                });

                if (response.ok) {
                    const result = await response.json();
                    app.extensionManager.toast.add({
                        severity: "success",
                        summary: "预览图上传",
                        detail: result.message || "预览图已保存",
                        life: 2000,
                    });
                    overlay.remove();
                    onUploaded?.();
                } else {
                    const error = await response.text();
                    app.extensionManager.toast.add({
                        severity: "error",
                        summary: "上传失败",
                        detail: `上传失败: ${error}`,
                        life: 3000,
                    });
                    confirmBtn.textContent = "确认上传";
                    confirmBtn.disabled = false;
                    confirmBtn.style.opacity = "1";
                }
            } catch (e) {
                app.extensionManager.toast.add({
                    severity: "error",
                    summary: "上传出错",
                    detail: `上传出错: ${e.message}`,
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
    };

    input.click();
}
