/**
 * ComfyUI 工作流自动同步扩展
 *
 * 监听 ComfyUI 前端画布的工作流变更，自动将 API 格式的工作流 JSON
 * 同步到后端 /comfyui-txtnode/save_workflow，供 UXP 插件拉取。
 *
 * 使用防抖机制避免频繁请求（默认 1500ms 延迟）。
 */

import { app } from "../../../scripts/app.js";

const SYNC_DELAY_MS = 1500; // 防抖延迟
const API_PATH = "/comfyui-txtnode/save_workflow";

app.registerExtension({
    name: "Comfyui-txtnode.WorkflowSync",

    async setup() {
        let saveTimer = null;
        let isSaving = false;

        /**
         * 将当前工作流序列化为 API 格式并发送到后端
         */
        async function syncWorkflow() {
            if (isSaving) return;
            isSaving = true;

            try {
                // 使用 ComfyUI 内置方法获取 API 格式工作流
                let workflow;
                try {
                    // app.graphToPrompt() 返回 { output: {...}, workflow: {...} }
                    // 其中 output 字段即为 API 格式的工作流 JSON
                    const prompt = await app.graphToPrompt();
                    workflow = prompt.output;
                } catch (e) {
                    // 备选：手动序列化
                    console.warn(
                        "[WorkflowSync] graphToPrompt 失败，使用手动序列化:",
                        e
                    );
                    workflow = manualSerializeGraph();
                }

                if (!workflow || Object.keys(workflow).length === 0) {
                    console.log("[WorkflowSync] 工作流为空，跳过同步");
                    return;
                }

                const resp = await fetch(API_PATH, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ workflow: workflow })
                });

                if (resp.ok) {
                    const result = await resp.json();
                    console.log(
                        `[WorkflowSync] 工作流已同步 (${result.node_count} 个节点)`
                    );
                } else {
                    console.warn(
                        "[WorkflowSync] 同步失败: HTTP",
                        resp.status
                    );
                }
            } catch (e) {
                console.warn("[WorkflowSync] 同步出错:", e.message || e);
            } finally {
                isSaving = false;
            }
        }

        /**
         * 手动序列化：遍历 app.graph._nodes 构建 API 格式工作流
         * 作为 graphToPrompt 不可用时的备选方案
         */
        function manualSerializeGraph() {
            var workflow = {};
            var nodes = app.graph._nodes || app.graph.nodes || [];

            for (var i = 0; i < nodes.length; i++) {
                var node = nodes[i];
                var nodeData = {
                    class_type: node.type,
                    inputs: {}
                };

                // 从 widgets 提取输入值
                if (node.widgets) {
                    for (var j = 0; j < node.widgets.length; j++) {
                        var w = node.widgets[j];
                        nodeData.inputs[w.name] = w.value;
                    }
                }

                // 从 inputs（连线）提取上游连接
                if (node.inputs) {
                    for (var k = 0; k < node.inputs.length; k++) {
                        var input = node.inputs[k];
                        if (input.link !== undefined && input.link !== null) {
                            var link = app.graph.links[input.link];
                            if (link) {
                                var originNode = app.graph.getNodeById(link.origin_id);
                                nodeData.inputs[input.name] = [
                                    String(link.origin_id),
                                    link.origin_slot
                                ];
                            }
                        }
                    }
                }

                workflow[String(node.id)] = nodeData;
            }

            return workflow;
        }

        /**
         * 触发防抖同步（1500ms 内多次调用只执行一次）
         */
        function debouncedSync() {
            if (saveTimer) clearTimeout(saveTimer);
            saveTimer = setTimeout(syncWorkflow, SYNC_DELAY_MS);
        }

        // ========== 监听图变更事件 ==========

        // 方案1: 使用 LiteGraph 的 onNodeAdded / onNodeRemoved / onConnectionChange
        const originalOnNodeAdded = app.graph.onNodeAdded;
        app.graph.onNodeAdded = function (node) {
            if (originalOnNodeAdded) {
                originalOnNodeAdded.apply(this, arguments);
            }
            debouncedSync();
        };

        const originalOnNodeRemoved = app.graph.onNodeRemoved;
        app.graph.onNodeRemoved = function (node) {
            if (originalOnNodeRemoved) {
                originalOnNodeRemoved.apply(this, arguments);
            }
            debouncedSync();
        };

        // 监听连线变更
        const originalAfterChange = app.graph.afterChange;
        if (originalAfterChange) {
            app.graph.afterChange = function () {
                originalAfterChange.apply(this, arguments);
                debouncedSync();
            };
        }

        // 方案2: hook app.queuePrompt，执行前强制同步
        const origQueuePrompt = app.queuePrompt;
        if (origQueuePrompt) {
            app.queuePrompt = async function () {
                // 执行前强制同步一次（确保最新状态已保存）
                if (saveTimer) {
                    clearTimeout(saveTimer);
                    await syncWorkflow();
                }
                return origQueuePrompt.apply(this, arguments);
            };
        }

        console.log("[WorkflowSync] 工作流自动同步已启用 (防抖 " + SYNC_DELAY_MS + "ms)");
    }
});
