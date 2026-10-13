/**
 * 当前工作流名解析（ComfyUI 前端共享工具）
 *
 * 供 workflow_sync.js（随 save_workflow 上报）与 ps_sync_on_run.js
 * （随 request_sync 上报）共用，避免两处重复实现。
 *
 * 名字语义 = 用户保存/加载的工作流的文件名/标签名（如「线稿」）。
 * 多级回退取不到、或取到占位名（Untitled 等）时返回空串，
 * 由调用方决定不上报（插件侧据此不显示该行，见 ADR-0096）。
 *
 * 注意：本模块刻意不 import app，由调用方传入（各前端脚本的
 * "…/scripts/app.js" 相对路径与扩展 URL 命名空间耦合，集中导入更稳）。
 */

/** 视为「无有效名字」的占位值（小写比较；含 ComfyUI 默认的临时工作流名） */
const INVALID_NAMES = [
    "untitled",
    "未命名工作流",
    "未命名",
    "unnamed",
    "unsaved workflow",
    "unsaved",
];

/** 左侧导航/标签标题的固定后缀（ComfyUI 把标签标题设为「<工作流名> - ComfyUI」） */
const TAB_TITLE_SUFFIX = /\s*-\s*ComfyUI\s*$/i;

/** 归一化：去空白、剔除占位名，无效返回空串 */
export function sanitizeWorkflowName(name) {
    const s = String(name == null ? "" : name).trim();
    if (!s) return "";
    if (INVALID_NAMES.indexOf(s.toLowerCase()) !== -1) return "";
    return s;
}

/** 从工作流路径取文件名（去目录、去 .json 后缀） */
function basename(path) {
    const s = String(path == null ? "" : path).trim();
    if (!s) return "";
    const last = s.split(/[\\/]/).pop() || "";
    return last.replace(/\.json$/i, "");
}

/**
 * 从标签标题取工作流名：ComfyUI 用 "<工作流名> - ComfyUI" 作为 document.title，
 * 未打开命名工作流时为默认标题（ComfyUI），此时返回空串。
 */
function nameFromTabTitle() {
    try {
        const title = String(document.title || "").trim();
        if (!title) return "";
        const stripped = title.replace(TAB_TITLE_SUFFIX, "").trim();
        if (!stripped || stripped.toLowerCase() === "comfyui") return "";
        return sanitizeWorkflowName(stripped);
    } catch (e) {
        return "";
    }
}

/**
 * 取当前工作流名，多级回退（访问器与字段名随 ComfyUI 前端版本而异）：
 *   1. 当前工作流对象：filename（ComfyUI 1.5x 实际字段）→ name → path 去目录/后缀
 *      （对象来自 app.workflowManager.activeWorkflow 或 app.extensionManager.workflow.activeWorkflow）
 *   2. app.graph.extra.workflowName / extra.name
 *   3. URL ?workflow= 参数（插件「自定义工作流」按钮打开时携带）
 *   4. 标签标题 "<工作流名> - ComfyUI"（与前端内部实现解耦的兜底）
 * 全部取不到或无效时返回 ""。
 *
 * @param {object} app ComfyUI 前端 app 对象
 */
export function getWorkflowName(app) {
    if (!app) return "";

    // 1) 当前工作流对象的候选字段
    try {
        const mgr = app.workflowManager;
        const aw =
            (mgr && mgr.activeWorkflow) ||
            (app.extensionManager &&
                app.extensionManager.workflow &&
                app.extensionManager.workflow.activeWorkflow);
        if (aw) {
            const candidates = [aw.filename, aw.name, basename(aw.path)];
            for (const c of candidates) {
                const n = sanitizeWorkflowName(c);
                if (n) return n;
            }
        }
    } catch (e) {
        // 访问器不存在时静默回退（前端版本差异）
    }

    // 2) graph.extra
    try {
        const extra = app.graph && app.graph.extra;
        if (extra) {
            const n = sanitizeWorkflowName(extra.workflowName || extra.name);
            if (n) return n;
        }
    } catch (e) {
        // 忽略
    }

    // 3) URL 参数
    try {
        const p = new URLSearchParams(window.location.search).get("workflow");
        const n = sanitizeWorkflowName(p);
        if (n) return n;
    } catch (e) {
        // 忽略
    }

    // 4) 标签标题兜底
    return nameFromTabTitle();
}