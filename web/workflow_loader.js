/**
 * ComfyUI 预设工作流加载扩展
 *
 * 检测 URL 参数 ?workflow=xxx，自动从后端加载预设工作流到画布。
 * 用于 UXP 插件"自定义工作流"按钮快速打开预设工作流。
 *
 * 使用方式:
 *   浏览器打开 http://127.0.0.1:8188/?workflow=web
 *   前端扩展自动检测参数，调用 /comfyui-txtnode/load_workflow?name=web
 *   获取工作流数据后使用 app.loadGraphData() 加载到画布
 */

import { app } from "../../../scripts/app.js";

const API_PATH = "/comfyui-txtnode/load_workflow";

app.registerExtension({
    name: "Comfyui-txtnode.WorkflowLoader",

    async setup() {
        // 检测 URL 参数
        const params = new URLSearchParams(window.location.search);
        const workflowName = params.get("workflow");

        if (!workflowName) {
            // 无参数，不执行任何操作
            return;
        }

        console.log("[WorkflowLoader] 检测到工作流参数: " + workflowName);

        try {
            // 调用后端 API 获取工作流数据
            const resp = await fetch(API_PATH + "?name=" + encodeURIComponent(workflowName));

            if (!resp.ok) {
                // 404 = 插件版本过旧，没有此端点
                if (resp.status === 404) {
                    console.warn("[WorkflowLoader] 加载失败: 插件版本过旧，请升级 Comfyui-txtnode 插件");
                    // 显示 ComfyUI toast 提示
                    if (app.ui && app.ui.toast) {
                        app.ui.toast.show({
                            type: "error",
                            message: "请升级 Comfyui-txtnode 插件以使用自定义工作流功能"
                        });
                    } else {
                        // 备选：使用 alert
                        alert("请升级 Comfyui-txtnode 插件以使用自定义工作流功能");
                    }
                } else {
                    console.warn("[WorkflowLoader] 加载失败: HTTP " + resp.status);
                }
                return;
            }

            const data = await resp.json();
            const workflow = data.workflow;

            if (!workflow) {
                console.warn("[WorkflowLoader] 响应中无工作流数据");
                return;
            }

            // 加载工作流到画布
            // 延迟执行，确保 ComfyUI 画布已完全初始化
            console.log("[WorkflowLoader] 加载预设工作流: " + workflowName);
            setTimeout(function() {
                try {
                    app.loadGraphData(workflow);
                    console.log("[WorkflowLoader] 工作流加载完成");
                } catch (e) {
                    console.error("[WorkflowLoader] loadGraphData 失败:", e);
                }
            }, 500);

        } catch (e) {
            console.error("[WorkflowLoader] 加载出错:", e);
        }
    }
});
