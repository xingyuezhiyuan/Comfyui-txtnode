import { app } from "../../../scripts/app.js";

// 为 V3 节点"是否存在"(TxtNodeAnyExists) 同步万能插槽的类型与中文标签。
// V3 后端参数名固定为 schema 英文 id（any / gh_input_type），因此只需改
// 插槽的 type 与 label，无需像 V1 那样重命名 input.name 或做中文 key 反映射。
app.registerExtension({
    name: "txtnode.any_exists",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "TxtNodeAnyExists") return;

        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            originalCreated?.apply(this, arguments);
            this._ghAnyType = "ANY";
            this.size[0] = Math.max(this.size[0] || 0, 210);
            this._ghEnsureTypeWidget?.();
            requestAnimationFrame(() => this._ghSyncAnyType?.());
        };

        // gh_input_type 由后端 schema 自动生成 widget，这里负责隐藏它。
        nodeType.prototype._ghEnsureTypeWidget = function () {
            let widget = this.widgets?.find((w) => w.name === "gh_input_type");
            if (widget) {
                widget.type = "hidden";
                widget.hidden = true;
                widget.computeSize = () => [0, 0];
                widget.draw = () => {};
                widget.mouse = () => false;
            }
            this.serialize_widgets = true;
            return widget;
        };

        const originalConnections = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (type, index, connected, linkInfo) {
            originalConnections?.apply(this, arguments);
            // LiteGraph 触发本事件时，graph.links 可能尚未完成写入。
            requestAnimationFrame(() => this._ghSyncAnyType?.());
        };

        nodeType.prototype._ghSyncAnyType = function () {
            // 移除重复的 any 插槽，优先保留已连接的插槽。
            const aliases = new Set([
                "any", "Any", "图像", "遮罩", "音频", "视频", "模型", "CLIP", "VAE",
                "字符串", "条件", "Latent", "整数", "浮点", "布尔"
            ]);
            const candidates = (this.inputs || [])
                .map((slot, index) => ({ slot, index }))
                .filter(({ slot }) => aliases.has(slot.name) || aliases.has(slot.label));
            const kept = candidates.find(({ slot }) => slot.link != null) || candidates[0];
            for (let i = candidates.length - 1; i >= 0; i--) {
                const candidate = candidates[i];
                if (kept && candidate.slot !== kept.slot && candidate.slot.link == null) {
                    this.removeInput(candidate.index);
                }
            }
            const input = kept?.slot || this.inputs?.[0];
            let detected = "ANY";
            if (input?.link != null && this.graph?.links) {
                const link = this.graph.links[input.link];
                const origin = link && this.graph.getNodeById(link.origin_id);
                const output = origin?.outputs?.[link.origin_slot];
                if (output?.type && output.type !== "*") detected = String(output.type).toUpperCase();
            }
            this._ghAnyType = detected;
            const labelMap = {
                IMAGE: "图像", MASK: "遮罩", AUDIO: "音频", VIDEO: "视频",
                MODEL: "模型", CLIP: "CLIP", VAE: "VAE", STRING: "字符串",
                CONDITIONING: "条件", LATENT: "Latent", INT: "整数", FLOAT: "浮点",
                BOOLEAN: "布尔", ANY: "Any"
            };
            const label = labelMap[detected] || detected;
            // V3：slot.name 保持后端英文 id 不变，仅改 type 与 label。
            if (input) {
                input.type = detected === "ANY" ? "*" : detected;
                input.label = label;
            }
            if (this.outputs) {
                const anyOutput = this.outputs[0];
                if (anyOutput) {
                    anyOutput.type = detected === "ANY" ? "*" : detected;
                    anyOutput.label = label;
                }
            }
            const widget = this._ghEnsureTypeWidget?.();
            if (widget) widget.value = detected;
            this.properties = this.properties || {};
            this.properties.gh_input_type = detected;
            this.size[0] = Math.max(this.size[0] || 0, 210);
            this.setDirtyCanvas?.(true, true);
        };

        const originalConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            originalConfigure?.apply(this, arguments);
            this._ghEnsureTypeWidget?.();
            requestAnimationFrame(() => this._ghSyncAnyType?.());
        };
    },
});
