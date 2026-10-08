/**
 * ComfyUI 当前工作流名实时同步扩展（ADR-0097）
 *
 * 目标：用户在 ComfyUI 切换工作流时，立即把当前工作流名上报给后端；
 * 后端经 /txtnode/ws 广播给 PS 插件，插件 Web 网页面板的徽标随之更新
 * （无需运行，也不再依赖"画布变更"这个不保证触发的信号）。
 *
 * 检测采用多信号合并（与 ComfyUI 前端内部实现解耦）：
 *   1. 页面加载后立即上报一次；
 *   2. MutationObserver 观察 <title>（ComfyUI 标签标题为 "<工作流名> - ComfyUI"）；
 *   3. 2s 定时比较兜底（防某版本切换时标题不更新）。
 *
 * 只在名字相对上次成功上报值变化时 POST（含变为空串 = 当前工作流没有名字）。
 */

import { app } from "../../../scripts/app.js";
import { getWorkflowName } from "./utils/workflow-name.js";

const API_PATH = "/comfyui-txtnode/set_workflow_name";
const COMPARE_INTERVAL_MS = 2000; // 定时比较间隔（兜底信号）
const INITIAL_DELAY_MS = 1500; // 页面加载后首次上报延迟（等前端初始化完成）

app.registerExtension({
    name: "Comfyui-txtnode.WorkflowNameSync",

    async setup() {
        // null = 尚未成功上报过（此时每次检测都尝试上报，直到成功一次）
        let lastReported = null;
        let reporting = false;

        async function reportIfChanged() {
            if (reporting) return;

            const name = getWorkflowName(app);
            if (lastReported !== null && name === lastReported) return;

            reporting = true;
            try {
                const resp = await fetch(API_PATH, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ workflow_name: name })
                });
                if (resp.ok) {
                    lastReported = name;
                    console.log(
                        "[WorkflowNameSync] 已同步工作流名: " + (name || "（无名字）")
                    );
                } else {
                    console.warn("[WorkflowNameSync] 同步失败: HTTP " + resp.status);
                }
            } catch (e) {
                console.warn(
                    "[WorkflowNameSync] 同步出错: " + (e && e.message ? e.message : e)
                );
            } finally {
                reporting = false;
            }
        }

        // 1) 页面加载后首次上报
        setTimeout(reportIfChanged, INITIAL_DELAY_MS);

        // 2) 观察标签标题变化（工作流切换时标题为 "<名字> - ComfyUI"）
        try {
            const titleEl = document.querySelector("title");
            if (titleEl) {
                new MutationObserver(reportIfChanged).observe(titleEl, {
                    childList: true,
                    characterData: true,
                    subtree: true
                });
            }
        } catch (e) {
            console.warn("[WorkflowNameSync] 观察标签标题失败: " + e);
        }

        // 3) 定时比较兜底
        setInterval(reportIfChanged, COMPARE_INTERVAL_MS);

        console.log("[WorkflowNameSync] 工作流名实时同步已启用");
    }
});