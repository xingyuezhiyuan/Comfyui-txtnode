import { app } from "../../../scripts/app.js";
import { saveTriggerWord, getTriggerWord } from "./utils/trigger-word-api.js";

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

            const result = await saveTriggerWord(loraName, triggerWord);

            if (result.success) {
                console.log(`[LoRALoaderModelOnly] 触发词已保存: ${loraName}`);
                app.extensionManager.toast.add({
                    severity: "success",
                    summary: "保存触发词",
                    detail: result.message || `已保存: ${loraName}`,
                    life: 2500,
                });
            } else {
                console.error("[LoRALoaderModelOnly]", result.message);
                app.extensionManager.toast.add({
                    severity: "error",
                    summary: "保存触发词",
                    detail: result.message,
                    life: 4000,
                });
            }
        };
        
        // 添加加载触发词的方法(当选择不同 LoRA 时调用)
        nodeType.prototype.loadTriggerWord = async function(loraName) {
            if (!loraName) return;

            const result = await getTriggerWord(loraName);
            const triggerWordWidget = this.widgets.find(w => w.name === "trigger_word");

            if (triggerWordWidget) {
                triggerWordWidget.value = result.trigger_word || "";
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
