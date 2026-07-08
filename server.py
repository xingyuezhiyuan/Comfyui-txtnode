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
