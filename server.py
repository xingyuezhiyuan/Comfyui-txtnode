import json
import server
from aiohttp import web
from pathlib import Path
from .lora_loader_node import load_trigger_words_config, save_trigger_words_config


def setup_routes():
    """注册 API 路由"""
    try:
        prompt_server = server.PromptServer.instance
        
        @prompt_server.routes.post("/comfyui-txtnode/save_trigger_word")
        async def save_trigger_word(request):
            """保存触发词到配置文件"""
            try:
                data = await request.json()
                lora_name = data.get("lora_name", "")
                trigger_word = data.get("trigger_word", "")
                
                if not lora_name:
                    return web.json_response(
                        {"error": "LoRA 名称不能为空"}, 
                        status=400
                    )
                
                config = load_trigger_words_config()
                
                if trigger_word.strip():
                    config[lora_name] = trigger_word.strip()
                else:
                    config.pop(lora_name, None)
                
                save_trigger_words_config(config)
                
                return web.json_response({
                    "success": True,
                    "message": f"已保存触发词: {lora_name}"
                })
                
            except Exception as e:
                return web.json_response(
                    {"error": str(e)}, 
                    status=500
                )
        
        @prompt_server.routes.get("/comfyui-txtnode/get_trigger_word")
        async def get_trigger_word(request):
            """获取指定 LoRA 的触发词"""
            try:
                lora_name = request.query.get("lora_name", "")
                
                if not lora_name:
                    return web.json_response(
                        {"error": "LoRA 名称不能为空"}, 
                        status=400
                    )
                
                config = load_trigger_words_config()
                trigger_word = config.get(lora_name, "")
                
                return web.json_response({
                    "lora_name": lora_name,
                    "trigger_word": trigger_word
                })
                
            except Exception as e:
                return web.json_response(
                    {"error": str(e)}, 
                    status=500
                )
        
        @prompt_server.routes.get("/comfyui-txtnode/get_all_trigger_words")
        async def get_all_trigger_words(request):
            """获取所有已保存的触发词"""
            try:
                config = load_trigger_words_config()
                # 转换成列表格式，按 LoRA 名称排序
                items = [
                    {"lora_name": k, "trigger_word": v}
                    for k, v in sorted(config.items(), key=lambda x: x[0].lower())
                ]
                return web.json_response({"trigger_words": items})
                
            except Exception as e:
                return web.json_response(
                    {"error": str(e)},
                    status=500
                )
        
        print("[Comfyui-txtnode] API 路由注册成功")
        
    except AttributeError as e:
        print(f"[Comfyui-txtnode] 路由注册失败: {e}")
        print("[Comfyui-txtnode] 将使用节点执行时保存的备选方案")


# 在模块加载时注册路由
setup_routes()
