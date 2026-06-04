/**
 * 触发词 API 封装模块
 * 统一处理与后端的触发词交互
 */

const API_BASE = "/comfyui-txtnode";

/**
 * 保存触发词到配置文件
 * @param {string} loraName - LoRA 文件名
 * @param {string} triggerWord - 触发词内容
 * @returns {Promise<{success: boolean, message: string}>}
 */
export async function saveTriggerWord(loraName, triggerWord) {
    try {
        const response = await fetch(`${API_BASE}/save_trigger_word`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                lora_name: loraName,
                trigger_word: triggerWord
            })
        });

        if (response.ok) {
            const result = await response.json();
            return { success: true, message: result.message };
        } else {
            return { success: false, message: `保存失败: ${response.statusText}` };
        }
    } catch (error) {
        return { success: false, message: `请求出错: ${error.message}` };
    }
}

/**
 * 获取指定 LoRA 的触发词
 * @param {string} loraName - LoRA 文件名
 * @returns {Promise<{lora_name: string, trigger_word: string}>}
 */
export async function getTriggerWord(loraName) {
    try {
        const response = await fetch(`${API_BASE}/get_trigger_word?lora_name=${encodeURIComponent(loraName)}`);

        if (response.ok) {
            return await response.json();
        }
        return { lora_name: loraName, trigger_word: "" };
    } catch (error) {
        console.error("[Comfyui-txtnode] 获取触发词失败:", error);
        return { lora_name: loraName, trigger_word: "" };
    }
}

/**
 * 获取所有已保存的触发词
 * @returns {Promise<Array<{lora_name: string, trigger_word: string}>>}
 */
export async function getAllTriggerWords() {
    try {
        const response = await fetch(`${API_BASE}/get_all_trigger_words`);

        if (response.ok) {
            const data = await response.json();
            return data.trigger_words || [];
        }
        return [];
    } catch (error) {
        console.error("[Comfyui-txtnode] 获取全部触发词失败:", error);
        return [];
    }
}
