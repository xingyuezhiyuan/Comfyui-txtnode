from comfy_api.latest import io


class IntJudgeNode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="IntJudgeNode",
            display_name="Int Judge",
            category="Utils",
            inputs=[
                io.Int.Input("input_value", force_input=True),
            ],
            outputs=[
                io.Int.Output("output_value"),
            ],
        )

    @classmethod
    def execute(cls, input_value):
        # 固定分档判断：<=1536 输出 400；1536<x<=3000 输出 800；>3000 输出 1200（含 >5000 封顶）
        if input_value <= 1536:
            output = 400
        elif input_value <= 3000:
            output = 800
        else:
            output = 1200
        return io.NodeOutput(output)
