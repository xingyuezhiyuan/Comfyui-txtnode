import { app } from "../../../scripts/app.js";
import { ComfyWidgets } from "../../../scripts/widgets.js";

app.registerExtension({
    name: "Comfyui-txtnode.LoRALoaderModelOnly",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // 检查是否是 LoRALoaderModelOnly 节点
        if (nodeData.name !== "LoRALoaderModelOnly") {
            return;
        }
        
        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        
        nodeType.prototype.onNodeCreated = function() {
            const result = originalOnNodeCreated ? originalOnNodeCreated.apply(this, arguments) : undefined;
            
            // 添加保存按钮
            const saveButton = this.addWidget("button", "保存触发词", null, () => {
                this.saveTriggerWord();
            });
            
            // 存储按钮引用
            this.saveTriggerButton = saveButton;
            
            // 获取 LoRA 名称下拉框组件
            const loraNameWidget = this.widgets.find(w => w.name === "lora_name");
            
            if (loraNameWidget) {
                // 包装 callback 以监听值变化
                const originalCallback = loraNameWidget.callback;
                loraNameWidget.callback = (value) => {
                    // 先执行原始回调
                    if (originalCallback) {
                        originalCallback(value);
                    }
                    // 自动加载新 LoRA 的触发词
                    console.log(`[LoRALoaderModelOnly] 切换 LoRA: ${value}`);
                    this.loadTriggerWord(value);
                };
                
                // 节点创建后延迟加载当前 LoRA 的触发词
                // 等待 widget 完全初始化
                setTimeout(() => {
                    if (loraNameWidget.value) {
                        console.log(`[LoRALoaderModelOnly] 初始化加载触发词: ${loraNameWidget.value}`);
                        this.loadTriggerWord(loraNameWidget.value);
                    }
                }, 200);
            }
            
            return result;
        };
        
        // 添加保存触发词的方法
        nodeType.prototype.saveTriggerWord = async function() {
            // 获取触发词输入框的值
            const triggerWordWidget = this.widgets.find(w => w.name === "trigger_word");
            const loraNameWidget = this.widgets.find(w => w.name === "lora_name");
            
            if (!triggerWordWidget || !loraNameWidget) {
                console.error("[LoRALoaderModelOnly] 找不到触发词或 LoRA 名称组件");
                return;
            }
            
            const triggerWord = triggerWordWidget.value;
            const loraName = loraNameWidget.value;
            
            if (!loraName) {
                app.extensionManager.toast.add({
                    severity: "warn",
                    summary: "保存触发词",
                    detail: "未选择 LoRA 模型",
                    life: 3000,
                });
                return;
            }
            
            try {
                // 通过 API 保存触发词
                const response = await fetch("/comfyui-txtnode/save_trigger_word", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        lora_name: loraName,
                        trigger_word: triggerWord
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    console.log(`[LoRALoaderModelOnly] 触发词已保存: ${loraName}`);
                    app.extensionManager.toast.add({
                        severity: "success",
                        summary: "保存触发词",
                        detail: result.message || `已保存: ${loraName}`,
                        life: 2500,
                    });
                } else {
                    const errMsg = `保存失败: ${response.statusText}`;
                    console.error("[LoRALoaderModelOnly]", errMsg);
                    app.extensionManager.toast.add({
                        severity: "error",
                        summary: "保存触发词",
                        detail: errMsg,
                        life: 4000,
                    });
                }
            } catch (error) {
                const errMsg = `请求出错: ${error.message}`;
                console.error("[LoRALoaderModelOnly]", errMsg);
                app.extensionManager.toast.add({
                    severity: "error",
                    summary: "保存触发词",
                    detail: errMsg,
                    life: 4000,
                });
            }
        };
        
        // 添加加载触发词的方法(当选择不同 LoRA 时调用)
        nodeType.prototype.loadTriggerWord = async function(loraName) {
            if (!loraName) return;
            
            try {
                const response = await fetch(`/comfyui-txtnode/get_trigger_word?lora_name=${encodeURIComponent(loraName)}`);
                
                if (response.ok) {
                    const result = await response.json();
                    const triggerWordWidget = this.widgets.find(w => w.name === "trigger_word");
                    
                    // 无论是否有触发词,都更新输入框(没有则清空)
                    if (triggerWordWidget) {
                        triggerWordWidget.value = result.trigger_word || "";
                    }
                }
            } catch (error) {
                console.error("[LoRALoaderModelOnly] 加载触发词时出错:", error);
            }
        };
        
        // 监听 LoRA 名称变化,自动加载触发词
        const originalGetExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
        nodeType.prototype.getExtraMenuOptions = function(_, options) {
            const result = originalGetExtraMenuOptions ? originalGetExtraMenuOptions.apply(this, arguments) : undefined;
            
            // 添加刷新触发词选项
            options.unshift({
                content: "刷新触发词",
                callback: () => {
                    const loraNameWidget = this.widgets.find(w => w.name === "lora_name");
                    if (loraNameWidget) {
                        this.loadTriggerWord(loraNameWidget.value);
                    }
                }
            });
            
            return result;
        };
    }
});
