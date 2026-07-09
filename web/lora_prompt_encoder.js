import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import { getTriggerWord } from "./utils/trigger-word-api.js";
import { showEditTriggerWordDialog, uploadLoraPreview } from "./utils/lora-actions.js";

/**
 * LoRA 提示词编码器 - 前端扩展
 *
 * 功能：
 * - LoRA 缩略图网格（支持搜索、分页、文件夹筛选）
 * - 多选 toggle 点击缩略图应用触发词
 * - 已选 LoRA 列表（含强度滑块）
 * - 正面/负面提示词 textarea
 */

// 分页选项
const PAGE_SIZES = [20, 40, 50, 70, 100, 0]; // 0 表示全部
const DEFAULT_PAGE_SIZE = 50;

// 缓存
let loraListCache = [];
let loraFoldersCache = [];
let lastFetchTime = 0;
const CACHE_TTL = 30000; // 30秒缓存

/**
 * 获取 LoRA 列表（从 object_info）
 */
async function fetchLoraList() {
    const now = Date.now();
    if (now - lastFetchTime < CACHE_TTL && loraListCache.length > 0) {
        return loraListCache;
    }

    try {
        // 从 object_info 获取 LoRA 列表
        const resp = await api.fetchApi("/object_info/LoraLoader");
        if (resp.ok) {
            const data = await resp.json();
            const loraNode = data["LoraLoader"];
            if (loraNode && loraNode.input) {
                const loraInput = loraNode.input.required?.lora_name || loraNode.input.optional?.lora_name;
                if (loraInput && Array.isArray(loraInput[0])) {
                    loraListCache = loraInput[0];
                    lastFetchTime = now;
                    // 提取文件夹列表
                    extractFolders();
                    return loraListCache;
                }
            }
        }
    } catch (e) {
        console.error("[LoRAPromptEncoder] 获取 LoRA 列表失败:", e);
    }
    return loraListCache;
}

/**
 * 从 LoRA 列表中提取文件夹结构
 */
function extractFolders() {
    const folders = new Set();
    folders.add("全部（可按文件夹排列）");

    for (const name of loraListCache) {
        if (name.includes("/") || name.includes("\\")) {
            const parts = name.split(/[\\/]/);
            // 添加所有层级的文件夹
            for (let i = 0; i < parts.length - 1; i++) {
                const folderPath = parts.slice(0, i + 1).join("/");
                folders.add(folderPath);
            }
        }
    }

    loraFoldersCache = Array.from(folders).sort((a, b) => {
        if (a === "全部（可按文件夹排列）") return -1;
        if (b === "全部（可按文件夹排列）") return 1;
        return a.localeCompare(b);
    });
}

/**
 * 获取 LoRA 的短名称（不含路径）
 */
function getShortName(name) {
    if (name.includes("/")) return name.split("/").pop();
    if (name.includes("\\")) return name.split("\\").pop();
    return name;
}

/**
 * 获取缩略图 URL
 */
function getThumbnailUrl(loraName) {
    const encoded = encodeURIComponent(loraName);
    return `/model_preview/get_image_by_name?folder_type=loras&filename=${encoded}&_t=${Date.now()}`;
}

/**
 * 创建 DOM 元素的辅助函数
 */
function el(tag, attrs = {}, children = []) {
    const elem = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
        if (key === "style" && typeof value === "object") {
            Object.assign(elem.style, value);
        } else if (key === "className") {
            elem.className = value;
        } else if (key.startsWith("on") && typeof value === "function") {
            elem.addEventListener(key.slice(2).toLowerCase(), value);
        } else if (key === "dataset") {
            for (const [dk, dv] of Object.entries(value)) {
                elem.dataset[dk] = dv;
            }
        } else {
            elem[key] = value;
        }
    }
    for (const child of children) {
        if (typeof child === "string") {
            elem.appendChild(document.createTextNode(child));
        } else if (child) {
            elem.appendChild(child);
        }
    }
    return elem;
}

/**
 * LoRA 提示词编码器节点扩展
 */
app.registerExtension({
    name: "Comfyui-txtnode.LoRAPromptEncoder",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "LoRAPromptEncoder") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);
            initNodeUI(this);
        };
    },
});

/**
 * 隐藏指定的 widget（不占用 UI 空间）
 */
function hideWidget(node, widgetName) {
    const widget = node.widgets?.find(w => w.name === widgetName);
    if (widget && !widget._hidden) {
        widget.hidden = true;
        widget._hidden = true;
        widget.computeSize = () => [0, -4];
    }
}

/**
 * 初始化节点 UI
 */
async function initNodeUI(node) {
    // 等待节点完全加载
    await new Promise(resolve => setTimeout(resolve, 100));

    // 隐藏内部数据传递用的 widget（不显示在 UI 上）
    hideWidget(node, "selected_loras");
    hideWidget(node, "positive_prompt_dom");
    hideWidget(node, "negative_prompt_dom");

    // 获取 LoRA 列表
    const loraList = await fetchLoraList();
    if (loraList.length === 0) {
        console.warn("[LoRAPromptEncoder] LoRA 列表为空");
        return;
    }

    // 状态管理
    const state = {
        selectedLoras: new Map(), // name -> {name, strength}
        searchQuery: "",
        currentFolder: "全部（可按文件夹排列）",
        currentPage: 0,
        pageSize: DEFAULT_PAGE_SIZE,
        positivePrompt: "",
        negativePrompt: "",
    };

    // 解析已选 LoRA（从 widget 恢复）
    const selectedLorasWidget = node.widgets?.find(w => w.name === "selected_loras");
    if (selectedLorasWidget?.value) {
        try {
            const saved = JSON.parse(selectedLorasWidget.value);
            for (const item of saved) {
                state.selectedLoras.set(item.name, item);
            }
        } catch (e) {
            console.error("[LoRAPromptEncoder] 解析已选 LoRA 失败:", e);
        }
    }

    // 创建主容器 - 左右布局
    const container = el("div", {
        className: "lora-prompt-encoder-container",
        style: {
            width: "100%",
            maxHeight: "600px",
            display: "flex",
            gap: "8px",
            background: "#1e1e1e",
            borderRadius: "4px",
            padding: "8px",
            boxSizing: "border-box",
            fontFamily: "Arial, sans-serif",
            fontSize: "12px",
            color: "#e0e0e0",
        },
    });

    // 左侧面板：正面/负面提示词 + 已选LoRA
    const leftPanel = el("div", {
        style: {
            flex: "1",
            minWidth: "200px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            overflow: "auto",
        },
    });

    // 正面提示词
    const positiveLabel = el("div", {
        style: { fontSize: "11px", color: "#888", marginBottom: "2px" },
    }, ["正面提示词"]);
    leftPanel.appendChild(positiveLabel);

    const positiveTextarea = el("textarea", {
        placeholder: "输入正面提示词...",
        style: {
            width: "100%",
            minHeight: "80px",
            padding: "6px 8px",
            background: "#2a2a2a",
            border: "1px solid #444",
            borderRadius: "4px",
            color: "#e0e0e0",
            fontSize: "12px",
            resize: "vertical",
            outline: "none",
            boxSizing: "border-box",
        },
        onInput: (e) => {
            state.positivePrompt = e.target.value;
            syncToWidget();
        },
    });
    leftPanel.appendChild(positiveTextarea);

    // 负面提示词
    const negativeLabel = el("div", {
        style: { fontSize: "11px", color: "#888", marginBottom: "2px" },
    }, ["负面提示词"]);
    leftPanel.appendChild(negativeLabel);

    const negativeTextarea = el("textarea", {
        placeholder: "输入负面提示词...",
        style: {
            width: "100%",
            minHeight: "60px",
            padding: "6px 8px",
            background: "#2a2a2a",
            border: "1px solid #444",
            borderRadius: "4px",
            color: "#e0e0e0",
            fontSize: "12px",
            resize: "vertical",
            outline: "none",
            boxSizing: "border-box",
        },
        onInput: (e) => {
            state.negativePrompt = e.target.value;
            syncToWidget();
        },
    });
    leftPanel.appendChild(negativeTextarea);

    // 已选 LoRA 列表
    const selectedContainer = el("div", {
        style: {
            background: "#252525",
            borderRadius: "4px",
            padding: "8px",
            flex: "1",
            overflow: "auto",
        },
    });

    const selectedTitle = el("div", {
        style: {
            fontSize: "11px",
            color: "#888",
            marginBottom: "6px",
        },
    }, ["已选 LoRA (0)"]);
    selectedContainer.appendChild(selectedTitle);

    const selectedList = el("div", {
        style: {
            display: "flex",
            flexDirection: "column",
            gap: "4px",
        },
    });
    selectedContainer.appendChild(selectedList);
    leftPanel.appendChild(selectedContainer);

    container.appendChild(leftPanel);

    // 右侧面板：搜索 + 控制栏 + 缩略图网格 + 分页
    const rightPanel = el("div", {
        style: {
            flex: "2",
            minWidth: "300px",
            display: "flex",
            flexDirection: "column",
            overflow: "auto",
        },
    });

    // 搜索框
    const searchInput = el("input", {
        type: "text",
        placeholder: "搜索 LoRA...",
        style: {
            width: "100%",
            padding: "6px 10px",
            background: "#2a2a2a",
            border: "1px solid #444",
            borderRadius: "4px",
            color: "#e0e0e0",
            fontSize: "12px",
            outline: "none",
            boxSizing: "border-box",
            marginBottom: "8px",
        },
        onInput: (e) => {
            state.searchQuery = e.target.value.toLowerCase();
            state.currentPage = 0;
            renderGrid();
        },
    });
    rightPanel.appendChild(searchInput);

    // 控制栏（文件夹 + 分页）
    const controlBar = el("div", {
        style: {
            display: "flex",
            gap: "8px",
            marginBottom: "8px",
            alignItems: "center",
        },
    });

    // 文件夹选择
    const folderSelect = el("select", {
        style: {
            flex: "1",
            padding: "4px 8px",
            background: "#2a2a2a",
            border: "1px solid #444",
            borderRadius: "4px",
            color: "#e0e0e0",
            fontSize: "11px",
            outline: "none",
        },
        onChange: (e) => {
            state.currentFolder = e.target.value;
            state.currentPage = 0;
            renderGrid();
        },
    });

    for (const folder of loraFoldersCache) {
        const option = el("option", { value: folder }, [folder]);
        folderSelect.appendChild(option);
    }
    controlBar.appendChild(folderSelect);

    // 分页选择
    const pageSelect = el("select", {
        style: {
            padding: "4px 8px",
            background: "#2a2a2a",
            border: "1px solid #444",
            borderRadius: "4px",
            color: "#e0e0e0",
            fontSize: "11px",
            outline: "none",
        },
        onChange: (e) => {
            state.pageSize = parseInt(e.target.value);
            state.currentPage = 0;
            renderGrid();
        },
    });

    for (const size of PAGE_SIZES) {
        const label = size === 0 ? "全部" : `${size}个/页`;
        const option = el("option", { value: size }, [label]);
        if (size === DEFAULT_PAGE_SIZE) option.selected = true;
        pageSelect.appendChild(option);
    }
    controlBar.appendChild(pageSelect);

    rightPanel.appendChild(controlBar);

    // 缩略图网格容器
    const gridContainer = el("div", {
        style: {
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(80px, 1fr))",
            gap: "6px",
            marginBottom: "8px",
            flex: "1",
            overflow: "auto",
        },
    });
    rightPanel.appendChild(gridContainer);

    // 分页控制
    const paginationBar = el("div", {
        style: {
            display: "flex",
            justifyContent: "center",
            gap: "4px",
            alignItems: "center",
        },
    });
    rightPanel.appendChild(paginationBar);

    container.appendChild(rightPanel);

    // 恢复提示词内容（从隐藏 DOM widget 恢复）
    const positiveDomWidget = node.widgets?.find(w => w.name === "positive_prompt_dom");
    const negativeDomWidget = node.widgets?.find(w => w.name === "negative_prompt_dom");
    if (positiveDomWidget?.value) {
        positiveTextarea.value = positiveDomWidget.value;
        state.positivePrompt = positiveDomWidget.value;
    }
    if (negativeDomWidget?.value) {
        negativeTextarea.value = negativeDomWidget.value;
        state.negativePrompt = negativeDomWidget.value;
    }

    /**
     * 过滤 LoRA 列表
     */
    function filterLoras() {
        let filtered = loraList;

        // 文件夹过滤
        if (state.currentFolder !== "全部（可按文件夹排列）") {
            const prefix = state.currentFolder + "/";
            filtered = filtered.filter(name => {
                const normalized = name.replace(/\\/g, "/");
                return normalized.startsWith(prefix);
            });
        }

        // 搜索过滤
        if (state.searchQuery) {
            filtered = filtered.filter(name =>
                name.toLowerCase().includes(state.searchQuery)
            );
        }

        return filtered;
    }

    /**
     * 渲染缩略图网格
     */
    function renderGrid() {
        gridContainer.innerHTML = "";
        paginationBar.innerHTML = "";

        const filtered = filterLoras();
        const total = filtered.length;

        // 计算分页
        let start = 0;
        let end = total;
        if (state.pageSize > 0) {
            start = state.currentPage * state.pageSize;
            end = Math.min(start + state.pageSize, total);
        }

        const pageItems = filtered.slice(start, end);

        // 渲染缩略图
        for (const loraName of pageItems) {
            const isSelected = state.selectedLoras.has(loraName);
            const card = createLoraCard(loraName, isSelected);
            gridContainer.appendChild(card);
        }

        // 渲染分页按钮
        if (state.pageSize > 0 && total > state.pageSize) {
            const totalPages = Math.ceil(total / state.pageSize);

            // 上一页
            const prevBtn = el("button", {
                style: {
                    padding: "4px 8px",
                    background: state.currentPage > 0 ? "#3a3a3a" : "#252525",
                    border: "1px solid #444",
                    borderRadius: "4px",
                    color: state.currentPage > 0 ? "#e0e0e0" : "#666",
                    fontSize: "11px",
                    cursor: state.currentPage > 0 ? "pointer" : "default",
                },
                onClick: () => {
                    if (state.currentPage > 0) {
                        state.currentPage--;
                        renderGrid();
                    }
                },
            }, ["上一页"]);
            paginationBar.appendChild(prevBtn);

            // 页码显示
            const pageInfo = el("span", {
                style: {
                    padding: "4px 8px",
                    color: "#888",
                    fontSize: "11px",
                },
            }, [`${state.currentPage + 1} / ${totalPages}`]);
            paginationBar.appendChild(pageInfo);

            // 下一页
            const nextBtn = el("button", {
                style: {
                    padding: "4px 8px",
                    background: state.currentPage < totalPages - 1 ? "#3a3a3a" : "#252525",
                    border: "1px solid #444",
                    borderRadius: "4px",
                    color: state.currentPage < totalPages - 1 ? "#e0e0e0" : "#666",
                    fontSize: "11px",
                    cursor: state.currentPage < totalPages - 1 ? "pointer" : "default",
                },
                onClick: () => {
                    if (state.currentPage < totalPages - 1) {
                        state.currentPage++;
                        renderGrid();
                    }
                },
            }, ["下一页"]);
            paginationBar.appendChild(nextBtn);
        }

        // 显示总数
        const totalInfo = el("span", {
            style: {
                padding: "4px 8px",
                color: "#666",
                fontSize: "11px",
            },
        }, [`共 ${total} 个`]);
        paginationBar.appendChild(totalInfo);
    }

    /**
     * 创建 LoRA 缩略图卡片
     */
    function createLoraCard(loraName, isSelected) {
        const shortName = getShortName(loraName);
        const thumbnailUrl = getThumbnailUrl(loraName);

        const card = el("div", {
            className: "lora-card",
            style: {
                position: "relative",
                aspectRatio: "1",
                borderRadius: "4px",
                overflow: "hidden",
                cursor: "pointer",
                border: isSelected ? "2px solid #4a9eff" : "2px solid transparent",
                transition: "border-color 0.2s",
            },
            onClick: () => toggleLora(loraName),
        });

        // 缩略图
        const img = el("img", {
            src: thumbnailUrl,
            style: {
                width: "100%",
                height: "100%",
                objectFit: "cover",
            },
        });

        img.onerror = () => {
            // 加载失败时隐藏图片，显示占位背景
            img.style.display = "none";
            card.style.background = "#3a3a3a";
        };

        card.appendChild(img);

        // 左上角悬浮按钮（左键修改触发词，右键修改缩略图）
        const floatBtn = el("div", {
            style: {
                position: "absolute",
                top: "3px",
                left: "3px",
                width: "16px",
                height: "16px",
                background: "rgba(30,30,34,0.7)",
                border: "1px solid rgba(102,102,102,0.5)",
                borderRadius: "3px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: "2",
            },
            title: "左键修改触发词，右键修改缩略图",
        });
        floatBtn.onmouseenter = () => {
            floatBtn.style.background = "rgba(74,106,176,0.8)";
            floatBtn.style.borderColor = "rgba(102,170,255,0.7)";
        };
        floatBtn.onmouseleave = () => {
            floatBtn.style.background = "rgba(30,30,34,0.7)";
            floatBtn.style.borderColor = "rgba(102,102,102,0.5)";
        };
        // 左键：修改触发词
        floatBtn.onclick = (e) => {
            e.stopPropagation();
            getTriggerWord(loraName).then(result => {
                showEditTriggerWordDialog(loraName, result.trigger_word || "", () => {
                    app.extensionManager.toast.add({
                        severity: "success",
                        summary: "触发词已更新",
                        detail: `已更新 ${shortName} 的触发词`,
                        life: 1500,
                    });
                    // 如果已选中，刷新已选列表提示
                    if (state.selectedLoras.has(loraName)) {
                        renderSelectedList();
                    }
                });
            });
        };
        // 右键：修改缩略图
        floatBtn.oncontextmenu = (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadLoraPreview(loraName, () => {
                // 恢复显示（如果之前因加载失败被隐藏）
                img.style.display = "";
                card.style.background = "";
                // 设置新 src 触发重新加载
                img.src = getThumbnailUrl(loraName);
                // 同步更新已选列表的缩略图
                if (state.selectedLoras.has(loraName)) {
                    renderSelectedList();
                }
            });
        };

        const floatBtnImg = el("img", {
            src: new URL("icon2.png", import.meta.url).href,
            style: {
                width: "10px",
                height: "10px",
                pointerEvents: "none",
            },
        });
        floatBtnImg.onerror = () => {
            floatBtn.textContent = "✎";
            floatBtn.style.fontSize = "11px";
        };
        floatBtn.appendChild(floatBtnImg);
        card.appendChild(floatBtn);

        // 名称覆盖层
        const nameOverlay = el("div", {
            style: {
                position: "absolute",
                bottom: "0",
                left: "0",
                right: "0",
                padding: "4px",
                background: "linear-gradient(transparent, rgba(0,0,0,0.8))",
                fontSize: "10px",
                color: "#fff",
                textOverflow: "ellipsis",
                overflow: "hidden",
                whiteSpace: "nowrap",
            },
            title: shortName,
        }, [shortName]);
        card.appendChild(nameOverlay);

        // 选中指示器
        if (isSelected) {
            const checkmark = el("div", {
                style: {
                    position: "absolute",
                    top: "4px",
                    right: "4px",
                    width: "16px",
                    height: "16px",
                    borderRadius: "50%",
                    background: "#4a9eff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "10px",
                    color: "#fff",
                },
            }, ["✓"]);
            card.appendChild(checkmark);
        }

        // 悬停效果
        card.onmouseenter = () => {
            if (!isSelected) {
                card.style.borderColor = "#666";
            }
        };
        card.onmouseleave = () => {
            if (!isSelected) {
                card.style.borderColor = "transparent";
            }
        };

        return card;
    }

    /**
     * 切换 LoRA 选中状态
     */
    async function toggleLora(loraName) {
        if (state.selectedLoras.has(loraName)) {
            // 取消选中
            state.selectedLoras.delete(loraName);
            // 从提示词中移除触发词和 LoRA 标签
            removeLoraFromPrompt(loraName);
        } else {
            // 选中
            const newItem = { name: loraName, strength: 1.0 };
            state.selectedLoras.set(loraName, newItem);
            // 添加触发词和 LoRA 标签
            await addLoraToPrompt(loraName);
        }

        renderGrid();
        renderSelectedList();
        syncToWidget();
    }

    /**
     * 添加 LoRA 到提示词（只添加触发词，不添加 LoRA 标签）
     */
    async function addLoraToPrompt(loraName) {
        // 获取并添加触发词
        try {
            const result = await getTriggerWord(loraName);
            const triggerWord = result.trigger_word || "";
            if (triggerWord && triggerWord.trim()) {
                let currentText = positiveTextarea.value;
                if (currentText && !currentText.endsWith(", ")) {
                    currentText += ", ";
                }
                currentText += triggerWord;
                positiveTextarea.value = currentText;
                state.positivePrompt = currentText;
            }
        } catch (e) {
            console.error("[LoRAPromptEncoder] 获取触发词失败:", e);
        }

        syncToWidget();
    }

    /**
     * 从提示词中移除 LoRA 触发词
     */
    function removeLoraFromPrompt(loraName) {
        let text = positiveTextarea.value;

        // 获取触发词并移除
        getTriggerWord(loraName).then(result => {
            const triggerWord = result.trigger_word || "";
            if (triggerWord && triggerWord.trim()) {
                const triggerRegex = new RegExp(escapeRegex(triggerWord) + "\\s*,?\\s*", "g");
                text = text.replace(triggerRegex, "");
                // 清理末尾的逗号和空格
                text = text.replace(/,\s*$/, "");
                positiveTextarea.value = text;
                state.positivePrompt = text;
                syncToWidget();
            }
        }).catch(() => {});
    }

    /**
     * 转义正则表达式特殊字符
     */
    function escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }

    /**
     * 渲染已选 LoRA 列表
     */
    function renderSelectedList() {
        selectedList.innerHTML = "";
        selectedTitle.textContent = `已选 LoRA (${state.selectedLoras.size})`;

        if (state.selectedLoras.size === 0) {
            selectedList.appendChild(el("div", {
                style: { color: "#666", fontSize: "11px", textAlign: "center", padding: "8px" },
            }, ["未选择 LoRA"]));
            return;
        }

        for (const [name, item] of state.selectedLoras) {
            const shortName = getShortName(name);
            const thumbnailUrl = getThumbnailUrl(name);

            const row = el("div", {
                style: {
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "6px",
                    background: "#2a2a2a",
                    borderRadius: "4px",
                },
            });

            // 缩略图
            const thumb = el("img", {
                src: thumbnailUrl,
                style: {
                    width: "32px",
                    height: "32px",
                    borderRadius: "4px",
                    objectFit: "cover",
                },
            });
            thumb.onerror = () => {
                thumb.style.background = "#3a3a3a";
                thumb.src = "";
            };
            row.appendChild(thumb);

            // 名称
            const nameSpan = el("span", {
                style: {
                    flex: "1",
                    fontSize: "11px",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                },
                title: shortName,
            }, [shortName]);
            row.appendChild(nameSpan);

            // 操作按钮容器（按钮 + 提示文字）
            const actionContainer = el("div", {
                style: {
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "2px",
                    flexShrink: "0",
                },
            });

            // 操作按钮（左键修改触发词，右键修改缩略图）
            const actionBtn = el("div", {
                style: {
                    width: "16px",
                height: "16px",
                    background: "rgba(58,58,62,0.6)",
                    border: "1px solid rgba(102,102,102,0.5)",
                    borderRadius: "3px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                },
                title: "左键修改触发词，右键修改缩略图",
            });
            actionBtn.onmouseenter = () => {
                actionBtn.style.background = "rgba(74,106,176,0.7)";
                actionBtn.style.borderColor = "rgba(102,170,255,0.7)";
            };
            actionBtn.onmouseleave = () => {
                actionBtn.style.background = "rgba(58,58,62,0.6)";
                actionBtn.style.borderColor = "rgba(102,102,102,0.5)";
            };
            // 左键：修改触发词
            actionBtn.onclick = (e) => {
                e.stopPropagation();
                getTriggerWord(name).then(result => {
                    showEditTriggerWordDialog(name, result.trigger_word || "", () => {
                        // 保存成功后刷新
                        app.extensionManager.toast.add({
                            severity: "success",
                            summary: "触发词已更新",
                            detail: `已更新 ${shortName} 的触发词`,
                            life: 1500,
                        });
                        // 刷新列表以更新提示文字
                        renderSelectedList();
                    });
                });
            };
            // 右键：修改缩略图
            actionBtn.oncontextmenu = (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadLoraPreview(name, () => {
                    // 刷新已选列表以更新缩略图和提示文字
                    renderSelectedList();
                    // 同步更新网格区域的缩略图
                    renderGrid();
                });
            };

            const btnImg = el("img", {
                src: new URL("icon.png", import.meta.url).href,
                style: {
                    width: "14px",
                    height: "14px",
                    pointerEvents: "none",
                },
            });
            btnImg.onerror = () => {
                actionBtn.textContent = "⚙";
                actionBtn.style.fontSize = "10px";
            };
            actionBtn.appendChild(btnImg);
            actionContainer.appendChild(actionBtn);

            // 检查是否有触发词和预览图，如果没有则显示提示
            (async () => {
                let hasTriggerWord = false;
                let hasPreview = false;

                // 检查触发词
                try {
                    const result = await getTriggerWord(name);
                    hasTriggerWord = !!(result.trigger_word && result.trigger_word.trim());
                } catch (e) {
                    // 忽略错误
                }

                // 检查预览图
                try {
                    const previewUrl = getThumbnailUrl(name);
                    const response = await fetch(previewUrl, { method: "HEAD" });
                    hasPreview = response.ok;
                } catch (e) {
                    // 忽略错误
                }

                // 根据缺失情况显示不同提示文字
                if (!hasTriggerWord && !hasPreview) {
                    const hint = el("div", {
                        style: {
                            fontSize: "9px",
                            color: "#888",
                            textAlign: "center",
                            whiteSpace: "nowrap",
                        },
                    }, ["当前Lora没有触发词和预览图，请添加"]);
                    actionContainer.appendChild(hint);
                } else if (!hasTriggerWord) {
                    const hint = el("div", {
                        style: {
                            fontSize: "9px",
                            color: "#888",
                            textAlign: "center",
                            whiteSpace: "nowrap",
                        },
                    }, ["当前Lora没有触发词，请左键按钮添加"]);
                    actionContainer.appendChild(hint);
                } else if (!hasPreview) {
                    const hint = el("div", {
                        style: {
                            fontSize: "9px",
                            color: "#888",
                            textAlign: "center",
                            whiteSpace: "nowrap",
                        },
                    }, ["当前Lora没有预览图，请右键按钮添加"]);
                    actionContainer.appendChild(hint);
                }
            })();

            row.appendChild(actionContainer);

            // 强度滑块
            const strengthSlider = el("input", {
                type: "range",
                min: "0",
                max: "1.5",
                step: "0.01",
                value: item.strength.toString(),
                style: {
                    width: "80px",
                    cursor: "pointer",
                },
                onInput: (e) => {
                    item.strength = parseFloat(e.target.value);
                    strengthInput.value = item.strength.toFixed(2);
                    syncToWidget();
                },
            });
            row.appendChild(strengthSlider);

            // 强度输入框（与滑块双向同步）
            const strengthInput = el("input", {
                type: "number",
                min: "0",
                max: "1.5",
                step: "0.01",
                value: item.strength.toFixed(2),
                style: {
                    width: "48px",
                    fontSize: "11px",
                    color: "#ccc",
                    background: "#333",
                    border: "1px solid #555",
                    borderRadius: "3px",
                    textAlign: "center",
                    padding: "1px 2px",
                },
                onInput: (e) => {
                    let val = parseFloat(e.target.value);
                    if (isNaN(val)) return;
                    val = Math.max(0, Math.min(1.5, val));
                    item.strength = val;
                    strengthSlider.value = val.toString();
                    syncToWidget();
                },
                onBlur: (e) => {
                    let val = parseFloat(e.target.value);
                    if (isNaN(val)) val = 1.0;
                    val = Math.max(0, Math.min(1.5, val));
                    item.strength = val;
                    e.target.value = val.toFixed(2);
                    strengthSlider.value = val.toString();
                    syncToWidget();
                },
            });
            row.appendChild(strengthInput);

            // 删除按钮
            const removeBtn = el("button", {
                style: {
                    padding: "2px 6px",
                    background: "#444",
                    border: "none",
                    borderRadius: "4px",
                    color: "#e0e0e0",
                    fontSize: "10px",
                    cursor: "pointer",
                },
                onClick: () => toggleLora(name),
            }, ["✕"]);
            removeBtn.onmouseenter = () => removeBtn.style.background = "#666";
            removeBtn.onmouseleave = () => removeBtn.style.background = "#444";
            row.appendChild(removeBtn);

            selectedList.appendChild(row);
        }
    }

    /**
     * 同步状态到 widget
     */
    function syncToWidget() {
        // 同步已选 LoRA
        const selectedLorasWidget = node.widgets?.find(w => w.name === "selected_loras");
        if (selectedLorasWidget) {
            const arr = Array.from(state.selectedLoras.values());
            selectedLorasWidget.value = JSON.stringify(arr);
            selectedLorasWidget.callback?.(selectedLorasWidget.value);
        }

        // 同步正面提示词到隐藏 DOM widget
        const positiveDomWidget = node.widgets?.find(w => w.name === "positive_prompt_dom");
        if (positiveDomWidget) {
            positiveDomWidget.value = state.positivePrompt;
            positiveDomWidget.callback?.(state.positivePrompt);
        }

        // 同步负面提示词到隐藏 DOM widget
        const negativeDomWidget = node.widgets?.find(w => w.name === "negative_prompt_dom");
        if (negativeDomWidget) {
            negativeDomWidget.value = state.negativePrompt;
            negativeDomWidget.callback?.(state.negativePrompt);
        }
    }

    // 转发 wheel 事件到 canvas，让 ComfyUI 处理画布缩放
    // 仅当目标元素实际可滚动时才保留元素自身的滚动行为
    container.addEventListener("wheel", (e) => {
        const target = e.target;
        let isScrollable = false;

        if (target.tagName === "TEXTAREA") {
            // 仅当 textarea 内容超出高度、实际可滚动时才保留
            isScrollable = target.scrollHeight > target.clientHeight + 1;
        } else if (target.tagName === "SELECT") {
            isScrollable = true;
        } else if (target.tagName === "INPUT" && target.type === "range") {
            isScrollable = true;
        }

        if (!isScrollable) {
            // 转发事件到 canvas，让 ComfyUI 处理缩放
            const canvas = app.canvas?.canvas;
            if (canvas) {
                canvas.dispatchEvent(new WheelEvent("wheel", {
                    deltaX: e.deltaX,
                    deltaY: e.deltaY,
                    deltaZ: e.deltaZ,
                    deltaMode: e.deltaMode,
                    clientX: e.clientX,
                    clientY: e.clientY,
                    screenX: e.screenX,
                    screenY: e.screenY,
                    ctrlKey: e.ctrlKey,
                    shiftKey: e.shiftKey,
                    altKey: e.altKey,
                    metaKey: e.metaKey,
                    bubbles: true,
                    cancelable: true,
                }));
            }
            e.preventDefault();
            e.stopPropagation();
        }
    }, { passive: false });

    // 添加 DOM widget
    node.addDOMWidget("lora_prompt_encoder_ui", "lora_prompt_encoder_ui", container, {
        serialize: false,
    });

    // 初始渲染
    renderGrid();
    renderSelectedList();

    console.log("[LoRAPromptEncoder] UI 初始化完成", node.id);
}
