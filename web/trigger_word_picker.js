import { app } from "../../../scripts/app.js";

/**
 * 触发词选择器 — 为 CLIPTextEncode 节点添加触发词快捷按钮
 *
 * 参考 Prompt Assistant 的挂载策略：
 * - LiteGraph 模式：挂载到 widget.element.parentElement
 * - Vue 模式：挂载到 [data-node-id] 内 textarea 的父容器
 */

let triggerWordsCache = [];
let lastFetchTime = 0;
const CACHE_TTL = 5000;

async function fetchAllTriggerWords() {
    const now = Date.now();
    if (now - lastFetchTime < CACHE_TTL && triggerWordsCache.length > 0) return triggerWordsCache;
    try {
        const resp = await fetch("/comfyui-txtnode/get_all_trigger_words");
        if (resp.ok) { const d = await resp.json(); triggerWordsCache = d.trigger_words || []; lastFetchTime = now; }
    } catch (err) { console.error("[Comfyui-txtnode] 获取触发词失败:", err); }
    return triggerWordsCache;
}

function getLoadedLoraNames() {
    const names = new Set();
    if (!app.graph) return names;
    for (const n of app.graph._nodes) {
        if (n.type === "LoRALoaderModelOnly") {
            const w = n.widgets?.find(w => w.name === "lora_name");
            if (w?.value) names.add(w.value);
        }
    }
    return names;
}

function showPopup() {
    document.querySelector(".txtnode-tw-overlay")?.remove();

    const loadedNames = getLoadedLoraNames();
    const allWords = triggerWordsCache;
    let matched = allWords.filter(i => loadedNames.has(i.lora_name));
    if (!matched.length) matched = allWords;

    const ov = document.createElement("div");
    ov.className = "txtnode-tw-overlay";
    ov.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;";

    const pop = document.createElement("div");
    pop.style.cssText = "background:#2a2a2e;border:1px solid #555;border-radius:8px;min-width:360px;max-width:480px;max-height:70vh;display:flex;flex-direction:column;box-shadow:0 8px 32px rgba(0,0,0,0.5);";

    const hdr = document.createElement("div");
    hdr.style.cssText = "display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid #444;font-size:14px;font-weight:600;color:#e0e0e0;";
    hdr.innerHTML = '<span>选择触发词</span><button style="background:none;border:none;color:#999;cursor:pointer;font-size:16px;padding:0 4px;">✕</button>';
    hdr.querySelector("button").onclick = () => ov.remove();
    pop.appendChild(hdr);

    const list = document.createElement("div");
    list.style.cssText = "overflow-y:auto;padding:8px;flex:1;";
    if (!matched.length) {
        list.innerHTML = '<div style="padding:24px;text-align:center;color:#888;font-size:13px;">' +
            (loadedNames.size ? "已加载的 LoRA 暂无保存的触发词" : "工作流中未检测到 LoRA 节点") + '</div>';
    } else {
        for (const item of matched) {
            const r = document.createElement("div");
            r.style.cssText = "display:flex;align-items:center;padding:8px 10px;margin:2px 0;border-radius:6px;cursor:pointer;justify-content:space-between;";
            r.onmouseenter = () => r.style.background = "#3a3a3e";
            r.onmouseleave = () => r.style.background = "transparent";
            const short = item.lora_name.includes("\\") ? item.lora_name.split("\\").pop() : item.lora_name.includes("/") ? item.lora_name.split("/").pop() : item.lora_name;
            r.innerHTML = `<span style="font-size:13px;color:#fff;font-weight:500;flex:1;word-break:break-word;">${esc(item.trigger_word)}</span><span style="font-size:11px;color:#888;margin-left:8px;white-space:nowrap;max-width:140px;overflow:hidden;text-overflow:ellipsis;">${esc(short)}</span>`;
            r.onclick = () => {
                const tw = app.graph._nodes.find(n => n.type === "CLIPTextEncode")?.widgets?.find(w => w.name === "text");
                if (tw) {
                    tw.value = ((tw.value || "").trim() ? tw.value + ", " : "") + item.trigger_word;
                    tw.callback?.(tw.value);
                }
                ov.remove();
                app.extensionManager.toast.add({ severity: "success", summary: "已应用触发词", detail: item.trigger_word, life: 1500 });
            };
            list.appendChild(r);
        }
    }
    pop.appendChild(list);
    const ft = document.createElement("div");
    ft.style.cssText = "padding:8px 14px;border-top:1px solid #444;font-size:11px;color:#777;text-align:center;";
    ft.textContent = loadedNames.size ? `工作流中 ${loadedNames.size} 个 LoRA · ${matched.length}/${allWords.length} 个触发词` : `共 ${allWords.length} 个已保存触发词`;
    pop.appendChild(ft);
    ov.appendChild(pop);
    ov.onclick = e => { if (e.target === ov) ov.remove(); };
    document.body.appendChild(ov);
}
function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

/** 找到 textarea 的挂载容器 */
function getMountContainer(node) {
    // 方案 A: LiteGraph 模式 — widget.element.parentElement
    const tw = node.widgets?.find(w => w.name === "text");
    if (!tw) return null;

    const el = tw.element || tw.inputEl;
    if (el && el.tagName === "TEXTAREA") {
        // 检查是否在 DOM 中（可能被 Vue 接管后 detach）
        if (document.body.contains(el)) {
            return { textarea: el, parent: el.parentElement };
        }
    }

    // 方案 B: Vue 模式 — [data-node-id] 内查找 textarea
    const nc = document.querySelector(`[data-node-id="${node.id}"]`);
    if (nc) {
        const ta = nc.querySelector("textarea.p-textarea") || nc.querySelector("textarea");
        if (ta) return { textarea: ta, parent: ta.parentElement };
    }

    return null;
}

/** 注入按钮 */
function injectButton(node) {
    if (node._twBtn) return;
    node._twBtn = true;

    let attempts = 0;
    const poll = setInterval(() => {
        attempts++;
        const mc = getMountContainer(node);
        if (mc && mc.parent && !mc.parent.querySelector(".tw-btn")) {
            clearInterval(poll);

            // 确保父容器 relative 定位
            if (getComputedStyle(mc.parent).position === "static") {
                mc.parent.style.position = "relative";
            }

            // 确保 overflow 不裁剪
            ["overflow", "overflowX", "overflowY"].forEach(p => {
                if (getComputedStyle(mc.parent)[p] === "hidden") {
                    mc.parent.style[p] = "visible";
                }
            });

            // 用 div 而非 button，避免 PrimeVue 拦截
            const btn = document.createElement("div");
            btn.className = "tw-btn";
            btn.title = "选择触发词";
            btn.style.cssText = "position:absolute;left:7px;bottom:7px;z-index:999;" +
                "background:rgba(58,58,62,0.45);border:1px solid rgba(102,102,102,0.45);border-radius:3px;" +
                "cursor:pointer;width:20px;height:20px;display:flex;align-items:center;justify-content:center;" +
                "pointer-events:auto;user-select:none;";
            btn.onmouseenter = () => { btn.style.background = "rgba(74,106,176,0.6)"; btn.style.borderColor = "rgba(102,170,255,0.6)"; };
            btn.onmouseleave = () => { btn.style.background = "rgba(58,58,62,0.45)"; btn.style.borderColor = "rgba(102,102,102,0.45)"; };
            btn.onmousedown = (e) => e.stopPropagation();
            btn.onclick = (e) => { e.stopPropagation(); showPopup(); };

            // 从同目录加载图标（ComfyUI 自动 serve web 目录文件）
            const img = document.createElement("img");
            img.src = new URL("icon.png", import.meta.url).href;
            img.style.cssText = "width:16px;height:16px;pointer-events:none;";
            img.onerror = () => {
                // 加载失败时显示文字
                btn.textContent = "TW";
                Object.assign(btn.style, { fontSize:"10px", fontWeight:"700", color:"#ddd", fontFamily:"Arial,sans-serif", lineHeight:"1", padding:"2px 4px" });
            };
            btn.appendChild(img);

            mc.parent.appendChild(btn);
            console.log("[Comfyui-txtnode] TW 按钮已挂载", node.id);

            // MutationObserver: 当 PrimeVue 重新渲染移除按钮时自动恢复
            const observer = new MutationObserver(() => {
                if (!document.body.contains(btn)) {
                    if (!mc.parent.querySelector(".tw-btn")) {
                        mc.parent.appendChild(btn);
                        console.log("[Comfyui-txtnode] TW 按钮被移除后恢复", node.id);
                    }
                }
            });
            observer.observe(mc.parent, { childList: true, subtree: true });
            return;
        }
        if (attempts > 80) clearInterval(poll);
    }, 100);
}

app.registerExtension({
    name: "Comfyui-txtnode.TriggerWordPicker",

    async setup() {
        await fetchAllTriggerWords();
        app.api.addEventListener("execution_success", () => { triggerWordsCache = []; lastFetchTime = 0; });

        // 等待 graph 就绪后 hook onNodeAdded 并扫描已存节点
        const wait = setInterval(() => {
            if (!app.graph) return;
            clearInterval(wait);

            // 扫描已有节点
            [500, 2000, 5000].forEach(d => setTimeout(() => {
                for (const n of app.graph._nodes) {
                    if (n.type === "CLIPTextEncode") injectButton(n);
                }
            }, d));

            // 拦截新节点
            if (!app.graph._twHooked) {
                app.graph._twHooked = true;
                const orig = app.graph.onNodeAdded;
                app.graph.onNodeAdded = function (node) {
                    orig?.call(this, node);
                    if (node?.type === "CLIPTextEncode") {
                        [300, 1500, 4000].forEach(d => setTimeout(() => injectButton(node), d));
                    }
                };
            }
        }, 100);
    },
});
