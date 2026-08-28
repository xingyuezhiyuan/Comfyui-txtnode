/**
 * ComfyUI 前端扩展：运行按钮点击前自动从 PS 拉取画布+遮罩
 *
 * 流程：
 * 1. 拦截 app.queuePrompt（运行按钮入口）
 * 2. 检查工作流是否包含 GetImageFromPS 节点，不包含则直接放行
 * 3. POST /txtnode/request_sync → 后端广播 sync_request 给 PS 插件
 * 4. PS 插件执行导出+上传后调用 /txtnode/sync_done
 * 5. 后端广播 txtnode_sync_done 事件 → 本扩展收到后放行提交工作流
 *
 * 失败策略：PS 未连接、同步失败或超时（30 秒）时，
 * 提示后继续用 ComfyUI input 目录中已有的画布/遮罩执行。
 */
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const SYNC_TIMEOUT_MS = 30000; // 等待 PS 同步的最大时长
const TARGET_NODE = "GetImageFromPS";

// ========== 状态提示（浮动条） ==========
let toastEl = null;

function showToast(text, color) {
    if (!toastEl) {
        toastEl = document.createElement("div");
        toastEl.style.cssText =
            "position:fixed;top:12px;left:50%;transform:translateX(-50%);" +
            "z-index:9999;padding:8px 16px;border-radius:6px;font-size:13px;" +
            "color:#fff;pointer-events:none;white-space:nowrap;" +
            "box-shadow:0 2px 8px rgba(0,0,0,0.4);transition:opacity 0.3s;";
        document.body.appendChild(toastEl);
    }
    toastEl.textContent = text;
    toastEl.style.background = color || "rgba(60,60,60,0.9)";
    toastEl.style.opacity = "1";
    toastEl.style.display = "block";
}

let toastTimer = null;

function hideToast(delayMs) {
    if (toastTimer) {
        clearTimeout(toastTimer);
        toastTimer = null;
    }
    if (!toastEl) return;
    const el = toastEl;
    if (delayMs) {
        toastTimer = setTimeout(function () {
            el.style.opacity = "0";
            setTimeout(function () {
                el.style.display = "none";
            }, 350);
        }, delayMs);
    } else {
        el.style.opacity = "0";
        setTimeout(function () {
            el.style.display = "none";
        }, 350);
    }
}

// ========== 检测工作流是否包含目标节点 ==========
function workflowContainsPSNode() {
    const nodes = (app.graph && (app.graph._nodes || app.graph.nodes)) || [];
    for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];
        if (node.comfyClass === TARGET_NODE || node.type === TARGET_NODE) {
            return true;
        }
    }
    return false;
}

// ========== 等待同步完成事件 ==========
function waitForSyncDone(requestId) {
    return new Promise(function (resolve) {
        let settled = false;
        let timeoutId = null;

        const handler = (event) => {
            let data = event;
            if (event && event.detail) data = event.detail;
            if (!data || data.request_id !== requestId) return;
            settle({
                success: !!data.success,
                canvas_filename: data.canvas_filename || "",
                mask_filename: data.mask_filename || "",
                client_id: data.client_id || ""
            });
        };

        function settle(result) {
            if (settled) return;
            settled = true;
            if (timeoutId) clearTimeout(timeoutId);
            api.removeEventListener("txtnode_sync_done", handler);
            resolve(result);
        }

        api.addEventListener("txtnode_sync_done", handler);
        timeoutId = setTimeout(function () {
            settle({ success: false, canvas_filename: "", mask_filename: "", client_id: "" }); // 超时按失败处理，继续用旧图执行
        }, SYNC_TIMEOUT_MS);
    });
}

// ========== 注入每任务隔离文件名到 GetImageFromPS 节点 ==========
function findGetImageFromPSNodes() {
    const nodes = (app.graph && (app.graph._nodes || app.graph.nodes)) || [];
    return nodes.filter(function (node) {
        return (node.comfyClass === TARGET_NODE || node.type === TARGET_NODE);
    });
}

function setWidgetValue(node, name, value) {
    const w = node.widgets && node.widgets.find(function (x) { return x.name === name; });
    if (w) {
        w.value = value;
        if (typeof w.callback === "function") {
            try { w.callback(value); } catch (e) { /* 忽略回调异常 */ }
        }
    }
}

function injectPSFilenames(canvasFilename, maskFilename) {
    const nodes = findGetImageFromPSNodes();
    for (const node of nodes) {
        if (canvasFilename) setWidgetValue(node, "image_filename", canvasFilename);
        if (maskFilename) setWidgetValue(node, "mask_filename", maskFilename);
    }
}

// ========== 把客户端稳定 ID 注入 SendImageToPS 节点，实现浏览器路径输出按客户端隔离 ==========
function findSendImageToPSNodes() {
    const nodes = (app.graph && (app.graph._nodes || app.graph.nodes)) || [];
    return nodes.filter(function (node) {
        return (node.comfyClass === "SendImageToPS" || node.type === "SendImageToPS");
    });
}

function injectClientId(clientId) {
    if (!clientId) return;
    const nodes = findSendImageToPSNodes();
    for (const node of nodes) {
        setWidgetValue(node, "client_id", clientId);
    }
}

// ========== 主流程：运行前同步 ==========
async function syncBeforeRun() {
    if (!workflowContainsPSNode()) {
        return true; // 工作流不含该节点，直接放行
    }

    showToast("正在从 PS 同步画布与遮罩...", "rgba(30,100,200,0.9)");

    try {
        const resp = await fetch("/txtnode/request_sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: "{}"
        });
        if (!resp.ok) {
            showToast("同步请求失败，使用已有图像继续", "rgba(180,90,0,0.9)");
            hideToast(3000);
            return true;
        }
        const data = await resp.json();

        if (!data.client_count) {
            showToast("PS 插件未连接，使用已有图像继续", "rgba(180,90,0,0.9)");
            hideToast(3000);
            return true;
        }

        const syncDone = await waitForSyncDone(data.request_id);
        const success = syncDone.success;
        if (success) {
            // 把本次上传的每任务隔离文件名注入 GetImageFromPS 节点输入，确保读取该文件
            if (syncDone.canvas_filename || syncDone.mask_filename) {
                injectPSFilenames(syncDone.canvas_filename, syncDone.mask_filename);
            }
            // 把客户端稳定 ID 注入 SendImageToPS，使浏览器运行路径输出同样按客户端隔离（ADR-0035）
            if (syncDone.client_id) {
                injectClientId(syncDone.client_id);
            }
            showToast("画布同步完成", "rgba(40,140,60,0.9)");
            hideToast(2000);
        } else {
            showToast("PS 同步失败或超时，使用已有图像继续", "rgba(180,90,0,0.9)");
            hideToast(3000);
        }
        return true;
    } catch (e) {
        console.warn("[PSSyncOnRun] 同步过程出错:", e);
        showToast("同步过程出错，使用已有图像继续", "rgba(180,90,0,0.9)");
        hideToast(3000);
        return true;
    }
}

// ========== 注册扩展：hook app.queuePrompt ==========
app.registerExtension({
    name: "Comfyui-txtnode.PSSyncOnRun",

    async setup() {
        const origQueuePrompt = app.queuePrompt;
        if (!origQueuePrompt) {
            console.warn("[PSSyncOnRun] app.queuePrompt 不存在，无法拦截运行");
            return;
        }

        let syncing = false;

        app.queuePrompt = async function () {
            if (!syncing) {
                syncing = true;
                try {
                    await syncBeforeRun();
                } finally {
                    syncing = false;
                }
            }
            return origQueuePrompt.apply(this, arguments);
        };

        console.log("[PSSyncOnRun] 运行前 PS 同步已启用（超时 " + SYNC_TIMEOUT_MS / 1000 + " 秒）");
    }
});
