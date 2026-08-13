import server
import os
import json
import base64
import io
import folder_paths
from PIL import Image
from aiohttp import web
from pathlib import Path
from .nodes import trigger_word_manager

# 预览图最大边长（超过则等比缩放）
MAX_PREVIEW_SIDE = 512
# JPG 保存质量
PREVIEW_JPG_QUALITY = 85


def resize_image_if_needed(image_path):
    """检查图片是否需要缩放。
    
    如果最长边超过 MAX_PREVIEW_SIDE，等比缩放到最长边 = MAX_PREVIEW_SIDE，
    并转为 JPG 格式（quality=85）。
    小图（最长边 <= 512）不做任何处理。
    
    返回: (bytes, content_type) 或 None（表示无需缩放，调用方可直接返回原文件）
    """
    try:
        with Image.open(image_path) as img:
            w, h = img.size
            max_side = max(w, h)
            
            # 小图不需要缩放
            if max_side <= MAX_PREVIEW_SIDE:
                return None
            
            # 等比缩放
            ratio = MAX_PREVIEW_SIDE / max_side
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            
            # 转 RGB（处理 RGBA/P 模式）
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            
            img = img.resize((new_w, new_h), Image.LANCZOS)
            
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=PREVIEW_JPG_QUALITY, optimize=True)
            buf.seek(0)
            return (buf.getvalue(), "image/jpeg")
    except Exception as e:
        print(f"[ModelPreview] 图片缩放失败: {e}")
        return None


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
                    # 大图自动缩放为最长边 512px 的 JPG
                    resized = resize_image_if_needed(image_path)
                    if resized:
                        data_bytes, content_type = resized
                        return web.Response(
                            body=data_bytes,
                            content_type=content_type,
                            headers=headers
                        )
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

                # 大图自动缩放并转为 JPG（最长边 <= 512px）
                try:
                    img = Image.open(io.BytesIO(image_data))
                    w, h = img.size
                    max_side = max(w, h)
                    
                    if max_side > MAX_PREVIEW_SIDE:
                        # 等比缩放
                        ratio = MAX_PREVIEW_SIDE / max_side
                        new_w = int(w * ratio)
                        new_h = int(h * ratio)
                        if img.mode not in ("RGB", "L"):
                            img = img.convert("RGB")
                        img = img.resize((new_w, new_h), Image.LANCZOS)
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=PREVIEW_JPG_QUALITY, optimize=True)
                        image_data = buf.getvalue()
                        preview_path = base_path + ".jpg"
                        print(f"[ModelPreview] 大图已缩放: {w}x{h} -> {new_w}x{new_h}")
                    else:
                        # 小图保持原格式保存
                        preview_path = base_path + image_ext
                except Exception as e:
                    # PIL 处理失败时回退到原格式保存
                    print(f"[ModelPreview] 图片处理失败，回退保存原图: {e}")
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

        # ========== 风格提示词卡片 API ==========
        # 数据分离：默认卡片（插件目录，可被更新覆盖）+ 用户卡片（用户数据目录，不受插件更新影响）
        _default_card_dir = os.path.join(os.path.dirname(__file__), "card")
        _default_cards_file = os.path.join(_default_card_dir, "style_cards.json")
        
        # 用户数据目录（ComfyUI/user_data/style_cards/）
        _user_card_dir = os.path.join(folder_paths.base_path, "user_data", "style_cards")
        _user_cards_file = os.path.join(_user_card_dir, "user_cards.json")

        def _read_default_cards():
            """读取插件默认卡片（只读，插件更新会覆盖）"""
            if not os.path.exists(_default_cards_file):
                return []
            try:
                with open(_default_cards_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []

        def _read_user_cards():
            """读取用户自定义卡片"""
            if not os.path.exists(_user_cards_file):
                return []
            try:
                with open(_user_cards_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []

        def _write_user_cards(cards):
            """写入用户自定义卡片"""
            os.makedirs(_user_card_dir, exist_ok=True)
            with open(_user_cards_file, "w", encoding="utf-8") as f:
                json.dump(cards, f, ensure_ascii=False, indent=2)

        def _read_style_cards():
            """读取合并后的卡片列表（用户卡片同名覆盖默认）"""
            default_cards = _read_default_cards()
            user_cards = _read_user_cards()
            
            # 用 name 作为唯一键，用户卡片优先
            merged = {c["name"]: c for c in default_cards if "name" in c}
            for c in user_cards:
                if "name" in c:
                    merged[c["name"]] = c  # 用户卡片覆盖默认
            
            return list(merged.values())

        def _find_card_image(filename):
            """查找卡片图片（先查用户目录，再查默认目录）"""
            if not filename:
                return None
            # 先查用户目录
            user_path = os.path.join(_user_card_dir, filename)
            if os.path.exists(user_path):
                return user_path
            # 再查默认目录
            default_path = os.path.join(_default_card_dir, filename)
            if os.path.exists(default_path):
                return default_path
            return None

        @prompt_server.routes.get("/comfyui-txtnode/get_style_cards")
        async def get_style_cards(request):
            """获取所有风格卡片列表（合并默认 + 用户）"""
            try:
                cards = _read_style_cards()
                return web.json_response({"cards": cards})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @prompt_server.routes.get("/comfyui-txtnode/get_style_card_image")
        async def get_style_card_image(request):
            """获取风格卡片预览图（先查用户目录，再查默认目录）"""
            try:
                filename = request.rel_url.query.get("filename", "")
                if not filename:
                    return web.Response(status=400, text="缺少 filename 参数")

                image_path = _find_card_image(filename)
                if not image_path:
                    return web.Response(status=404, text="图片不存在")

                headers = {
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                }
                return web.FileResponse(image_path, headers=headers)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @prompt_server.routes.post("/comfyui-txtnode/add_style_card")
        async def add_style_card(request):
            """添加风格卡片到用户目录（不影响默认卡片）"""
            try:
                data = await request.json()
                name = data.get("name", "").strip()
                filename = data.get("filename", "").strip()
                image_base64 = data.get("image_base64", "")
                prompt = data.get("prompt", "")

                if not name:
                    return web.json_response({"error": "卡片名称不能为空"}, status=400)
                if not image_base64:
                    return web.json_response({"error": "图片数据不能为空"}, status=400)

                # 默认文件名 = 名称.png
                if not filename:
                    filename = name + ".png"

                # 解码 base64 图片
                try:
                    image_data = base64.b64decode(image_base64)
                except Exception as e:
                    return web.json_response({"error": f"图片数据解码失败: {e}"}, status=400)

                # 保存图片到用户目录
                os.makedirs(_user_card_dir, exist_ok=True)
                image_path = os.path.join(_user_card_dir, filename)
                with open(image_path, "wb") as f:
                    f.write(image_data)

                # 更新用户 JSON
                cards = _read_user_cards()
                # 检查是否已存在同名卡片
                cards = [c for c in cards if c.get("name") != name]
                cards.append({"name": name, "filename": filename, "prompt": prompt})
                _write_user_cards(cards)

                print(f"[Comfyui-txtnode] 风格卡片已添加到用户目录: {name}")
                return web.json_response({"success": True, "message": f"已添加卡片: {name}"})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @prompt_server.routes.post("/comfyui-txtnode/update_style_card")
        async def update_style_card(request):
            """更新风格卡片提示词（只更新用户目录中的卡片）"""
            try:
                data = await request.json()
                name = data.get("name", "").strip()
                prompt = data.get("prompt", "")

                if not name:
                    return web.json_response({"error": "卡片名称不能为空"}, status=400)

                # 先检查卡片是否在用户目录中
                user_cards = _read_user_cards()
                updated = False
                for card in user_cards:
                    if card.get("name") == name:
                        card["prompt"] = prompt
                        updated = True
                        break

                if updated:
                    _write_user_cards(user_cards)
                    print(f"[Comfyui-txtnode] 用户风格卡片已更新: {name}")
                    return web.json_response({"success": True, "message": f"已更新卡片: {name}"})

                # 如果卡片在默认目录中，复制到用户目录并更新
                default_cards = _read_default_cards()
                target = None
                for card in default_cards:
                    if card.get("name") == name:
                        target = card.copy()
                        break

                if target:
                    target["prompt"] = prompt
                    user_cards.append(target)
                    _write_user_cards(user_cards)
                    print(f"[Comfyui-txtnode] 默认风格卡片已复制到用户目录并更新: {name}")
                    return web.json_response({"success": True, "message": f"已更新卡片: {name}"})

                return web.json_response({"error": f"未找到卡片: {name}"}, status=404)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @prompt_server.routes.post("/comfyui-txtnode/delete_style_card")
        async def delete_style_card(request):
            """删除风格卡片（只删除用户目录中的卡片）"""
            try:
                data = await request.json()
                name = data.get("name", "").strip()

                if not name:
                    return web.json_response({"error": "卡片名称不能为空"}, status=400)

                # 只从用户目录删除
                user_cards = _read_user_cards()
                target = None
                remaining = []
                for card in user_cards:
                    if card.get("name") == name:
                        target = card
                    else:
                        remaining.append(card)

                if not target:
                    # 检查是否在默认目录中
                    default_cards = _read_default_cards()
                    for card in default_cards:
                        if card.get("name") == name:
                            return web.json_response({
                                "error": f"卡片 '{name}' 是默认卡片，无法删除。如需移除，请编辑提示词为空。"
                            }, status=403)
                    return web.json_response({"error": f"未找到卡片: {name}"}, status=404)

                # 删除用户目录中的图片文件
                filename = target.get("filename", "")
                if filename:
                    image_path = os.path.join(_user_card_dir, filename)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        print(f"[Comfyui-txtnode] 已删除用户卡片图片: {filename}")

                # 更新用户 JSON
                _write_user_cards(remaining)
                print(f"[Comfyui-txtnode] 用户风格卡片已删除: {name}")
                return web.json_response({"success": True, "message": f"已删除卡片: {name}"})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

    except AttributeError as e:
        print(f"[Comfyui-txtnode] 路由注册失败: {e}")
        print("[Comfyui-txtnode] 将使用节点执行时保存的备选方案")


# 在模块加载时注册路由
setup_routes()
