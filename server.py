import server
import os
import base64
import folder_paths
from aiohttp import web
from pathlib import Path
from .nodes import trigger_word_manager


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

                trigger_word_manager.save_trigger_word(lora_name, trigger_word)

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

                trigger_word = trigger_word_manager.get_trigger_word(lora_name)

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
                items = trigger_word_manager.get_all_trigger_words()
                return web.json_response({"trigger_words": items})

            except Exception as e:
                return web.json_response(
                    {"error": str(e)},
                    status=500
                )

        # ========== 工作流同步 API ==========
        # 内存中暂存当前工作流（仅供 UXP 插件通过 HTTP 拉取）
        _current_workflow = {}

        @prompt_server.routes.post("/comfyui-txtnode/save_workflow")
        async def save_workflow(request):
            """保存当前 ComfyUI 工作流 JSON（API 格式）

            ComfyUI 前端每次工作流变更时自动调用此 API，
            将当前工作流同步到后端内存中，供 UXP 插件拉取。
            """
            try:
                data = await request.json()
                workflow = data.get("workflow")
                if not workflow:
                    return web.json_response(
                        {"error": "缺少 workflow 参数"},
                        status=400
                    )

                nonlocal _current_workflow
                _current_workflow = workflow
                node_count = len(workflow) if isinstance(workflow, dict) else 0
                print(f"[Comfyui-txtnode] 工作流已同步，共 {node_count} 个节点")

                return web.json_response({
                    "success": True,
                    "node_count": node_count
                })

            except Exception as e:
                print(f"[Comfyui-txtnode] 保存工作流失败: {e}")
                return web.json_response(
                    {"error": str(e)},
                    status=500
                )

        @prompt_server.routes.get("/comfyui-txtnode/get_workflow")
        async def get_workflow(request):
            """获取当前保存的工作流 JSON（API 格式）

            UXP 插件在"运行"前调用此 API 获取最新工作流，
            用于扫描自定义节点并替换文件名参数。
            """
            try:
                nonlocal _current_workflow
                if not _current_workflow:
                    return web.json_response(
                        {"error": "暂无工作流，请先在 ComfyUI 中打开或修改工作流"},
                        status=404
                    )

                node_count = len(_current_workflow) if isinstance(_current_workflow, dict) else 0
                return web.json_response({
                    "workflow": _current_workflow,
                    "node_count": node_count
                })

            except Exception as e:
                print(f"[Comfyui-txtnode] 获取工作流失败: {e}")
                return web.json_response(
                    {"error": str(e)},
                    status=500
                )

        # ========== WebSocket 推送（向 UXP 插件推送渲染结果） ==========
        _txtnode_ps_clients = []  # {ws, clientId, ip}

        @prompt_server.routes.get("/txtnode/ws")
        async def txtnode_ws_handler(request):
            """WebSocket 端点 — UXP 插件持久连接。

            UXP 插件在面板加载时连接到此端点，
            后端通过此连接向 UXP 推送 render 消息（文件路径通知）。
            查询参数:
                platform: 客户端平台标识（"ps" = Photoshop UXP）
                clientId: 客户端唯一标识
            """
            ws = web.WebSocketResponse()
            await ws.prepare(request)

            client_id = request.query.get("clientId", "")
            platform = request.query.get("platform", "unknown")
            client_ip = request.remote

            nonlocal _txtnode_ps_clients

            if platform == "ps":
                client_info = {
                    "ws": ws,
                    "clientId": client_id,
                    "ip": client_ip
                }
                _txtnode_ps_clients.append(client_info)
                print(f"[Comfyui-txtnode] PS 客户端已连接: {client_id} ({client_ip}), 当前共 {len(_txtnode_ps_clients)} 个")

            try:
                async for msg in ws:
                    # 目前 UXP 端不主动发消息，保留扩展空间
                    if msg.type == web.WSMsgType.ERROR:
                        print(f"[Comfyui-txtnode] WebSocket 错误: {ws.exception()}")
            finally:
                # 断开时清理
                _txtnode_ps_clients = [
                    c for c in _txtnode_ps_clients
                    if c["clientId"] != client_id
                ]
                print(f"[Comfyui-txtnode] PS 客户端已断开: {client_id}, 剩余 {len(_txtnode_ps_clients)} 个")

            return ws

        async def _broadcast_to_ps(message):
            """向所有已连接的 PS 客户端广播 JSON 消息。"""
            nonlocal _txtnode_ps_clients
            disconnected = []
            for client in _txtnode_ps_clients:
                try:
                    await client["ws"].send_json(message)
                except Exception as e:
                    print(f"[Comfyui-txtnode] 广播失败 {client['clientId']}: {e}")
                    disconnected.append(client)
            # 清理已断开的客户端
            for dc in disconnected:
                if dc in _txtnode_ps_clients:
                    _txtnode_ps_clients.remove(dc)

        @prompt_server.routes.post("/txtnode/notify_render")
        async def notify_render(request):
            """内部 API — SendImageToPS 节点执行后调用。

            接收文件名列表，通过 WebSocket 广播轻量通知给所有已连接的 PS 客户端。
            PS 插件收到通知后主动通过 HTTP GET /view 下载图片。

            Body: {"filenames": ["SendImageToPS_00000_.png", ...]}
            """
            try:
                data = await request.json()
                filenames = data.get("filenames", [])

                if not filenames:
                    return web.json_response(
                        {"error": "缺少 filenames 参数"},
                        status=400
                    )

                # 广播轻量通知给所有 PS 客户端
                await _broadcast_to_ps({
                    "type": "render_ready",
                    "filenames": filenames
                })

                print(f"[Comfyui-txtnode] 渲染通知已广播: {len(filenames)} 个文件（轻量通知）")
                return web.json_response({
                    "success": True,
                    "client_count": len(_txtnode_ps_clients)
                })

            except Exception as e:
                print(f"[Comfyui-txtnode] 渲染通知失败: {e}")
                return web.json_response(
                    {"error": str(e)},
                    status=500
                )

        @prompt_server.routes.get("/txtnode/get_image_base64")
        async def get_image_base64(request):
            """UXP 端 HTTP 下载失败时的回退 API。

            返回 SendImageToPS 缓存的 Base64 PNG 数据。
            查询参数: filename - 要获取的文件名（如 SendImageToPS_00000_.png）
            """
            try:
                from .nodes.ps_bridge import _base64_cache

                filename = request.rel_url.query.get("filename", "")
                if not filename:
                    return web.json_response(
                        {"error": "缺少 filename 参数"},
                        status=400
                    )

                base64_data = _base64_cache.get(filename)
                if not base64_data:
                    return web.json_response(
                        {"error": f"缓存中未找到文件: {filename}"},
                        status=404
                    )

                return web.json_response({
                    "success": True,
                    "filename": filename,
                    "base64": base64_data
                })

            except Exception as e:
                print(f"[Comfyui-txtnode] 获取 Base64 缓存失败: {e}")
                return web.json_response(
                    {"error": str(e)},
                    status=500
                )

        print("[Comfyui-txtnode] API 路由注册成功")

        # ========== 模型预览图 API ==========
        @prompt_server.routes.get("/model_preview/get_image_by_name")
        async def get_model_preview(request):
            """根据模型名查找并返回同名预览图"""
            try:
                folder_type = request.rel_url.query.get("folder_type", "checkpoints")
                filename = request.rel_url.query.get("filename", "")
                
                if not filename:
                    return web.Response(status=400)

                # 支持的模型类型
                valid_types = ["checkpoints", "loras", "unet"]
                if folder_type not in valid_types:
                    folder_type = "checkpoints"

                # 获取模型文件路径
                file_path = folder_paths.get_full_path(folder_type, filename)
                
                # unet 类型 fallback 到 diffusion_models
                if not file_path and folder_type == "unet":
                    file_path = folder_paths.get_full_path("diffusion_models", filename)
                
                if not file_path:
                    return web.Response(status=404, text="Model file not found")

                # 查找同名预览图（优先级：png > jpg > jpeg > webp）
                base_path = os.path.splitext(file_path)[0]
                image_path = None
                
                for ext in [".png", ".jpg", ".jpeg", ".webp", ".PNG", ".JPG"]:
                    test_path = base_path + ext
                    if os.path.exists(test_path):
                        image_path = test_path
                        break
                
                if image_path:
                    headers = {
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0",
                    }
                    return web.FileResponse(image_path, headers=headers)
                else:
                    return web.Response(status=404, text="Preview image not found")

            except Exception as e:
                print(f"[ModelPreview] 错误: {e}")
                return web.Response(status=500)

        # ========== 模型预览图上传 API ==========
        @prompt_server.routes.post("/model_preview/upload_preview_image")
        async def upload_model_preview(request):
            """上传模型预览图（JSON + base64）"""
            try:
                data = await request.json()
                folder_type = data.get("folder_type", "")
                filename = data.get("filename", "")
                image_base64 = data.get("image_base64", "")
                image_ext = data.get("image_ext", ".png")
                
                # 验证参数
                if not folder_type or not filename or not image_base64:
                    return web.json_response(
                        {"error": "缺少必要参数"},
                        status=400
                    )

                # 支持的模型类型
                valid_types = ["checkpoints", "loras", "unet"]
                if folder_type not in valid_types:
                    folder_type = "checkpoints"

                # 获取模型文件路径
                model_path = folder_paths.get_full_path(folder_type, filename)
                
                # unet 类型 fallback 到 diffusion_models
                if not model_path and folder_type == "unet":
                    model_path = folder_paths.get_full_path("diffusion_models", filename)
                
                if not model_path:
                    return web.json_response(
                        {"error": "模型文件不存在"},
                        status=404
                    )

                # 解码 base64 图片数据
                try:
                    image_data = base64.b64decode(image_base64)
                except Exception as e:
                    return web.json_response(
                        {"error": f"图片数据解码失败: {e}"},
                        status=400
                    )

                # 构建预览图路径（模型同名，替换扩展名）
                base_path = os.path.splitext(model_path)[0]

                # 删除已有的预览图，避免旧文件残留导致新图不生效
                for ext in [".png", ".jpg", ".jpeg", ".webp", ".PNG", ".JPG"]:
                    old_path = base_path + ext
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                            print(f"[ModelPreview] 已删除旧预览图: {old_path}")
                        except OSError as e:
                            print(f"[ModelPreview] 删除旧预览图失败: {old_path}, {e}")

                preview_path = base_path + image_ext
                
                # 保存预览图
                with open(preview_path, "wb") as f:
                    f.write(image_data)
                
                print(f"[ModelPreview] 预览图已保存: {preview_path}")
                
                return web.json_response({
                    "success": True,
                    "message": f"预览图已保存",
                    "preview_path": preview_path
                })

            except Exception as e:
                print(f"[ModelPreview] 上传错误: {e}")
                return web.json_response(
                    {"error": str(e)},
                    status=500
                )

    except AttributeError as e:
        print(f"[Comfyui-txtnode] 路由注册失败: {e}")
        print("[Comfyui-txtnode] 将使用节点执行时保存的备选方案")


# 在模块加载时注册路由
setup_routes()
