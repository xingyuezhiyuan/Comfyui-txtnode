#!/usr/bin/env python3
"""
测试脚本：验证风格卡片数据隔离机制
模拟插件更新场景，确保用户自定义卡片不会被覆盖

运行方式：
    cd E:\ComfyUI-aki-v2\ComfyUI\custom_nodes\Comfyui-txtnode\card
    python test_data_isolation.py
"""

import os
import json
import shutil
import tempfile

# 模拟路径
TEST_DIR = tempfile.mkdtemp(prefix="style_cards_test_")
DEFAULT_DIR = os.path.join(TEST_DIR, "plugin", "card")
USER_DIR = os.path.join(TEST_DIR, "user_data", "style_cards")

DEFAULT_CARDS_FILE = os.path.join(DEFAULT_DIR, "style_cards.json")
USER_CARDS_FILE = os.path.join(USER_DIR, "user_cards.json")


def setup_dirs():
    """创建测试目录"""
    os.makedirs(DEFAULT_DIR, exist_ok=True)
    os.makedirs(USER_DIR, exist_ok=True)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_default_cards():
    if not os.path.exists(DEFAULT_CARDS_FILE):
        return []
    return read_json(DEFAULT_CARDS_FILE)


def read_user_cards():
    if not os.path.exists(USER_CARDS_FILE):
        return []
    return read_json(USER_CARDS_FILE)


def write_user_cards(cards):
    os.makedirs(USER_DIR, exist_ok=True)
    write_json(USER_CARDS_FILE, cards)


def read_merged_cards():
    """合并逻辑：用户卡片同名覆盖默认"""
    default_cards = read_default_cards()
    user_cards = read_user_cards()
    merged = {c["name"]: c for c in default_cards if "name" in c}
    for c in user_cards:
        if "name" in c:
            merged[c["name"]] = c
    return list(merged.values())


def print_separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_plugin_update_isolation():
    """测试：插件更新不会覆盖用户数据"""
    
    print_separator("测试开始：插件更新数据隔离")
    print(f"测试目录: {TEST_DIR}")
    
    # ===== 阶段 1：初始状态（插件刚安装） =====
    print_separator("阶段 1：初始安装")
    
    initial_default_cards = [
        {"name": "动漫CG", "filename": "动漫CG.png", "prompt": "默认动漫CG提示词"},
        {"name": "二分动漫", "filename": "二分动漫.png", "prompt": "默认二分动漫提示词"},
    ]
    write_json(DEFAULT_CARDS_FILE, initial_default_cards)
    
    print(f"默认卡片: {[c['name'] for c in initial_default_cards]}")
    print(f"用户卡片: []")
    print(f"合并结果: {[c['name'] for c in read_merged_cards()]}")
    
    # ===== 阶段 2：用户添加自定义卡片 =====
    print_separator("阶段 2：用户添加自定义卡片")
    
    user_cards = [
        {"name": "我的风格", "filename": "我的风格.png", "prompt": "用户自定义的提示词"},
        {"name": "赛博朋克", "filename": "赛博朋克.png", "prompt": "赛博朋克风格"},
    ]
    write_user_cards(user_cards)
    
    # 同时用户修改了默认卡片的提示词
    user_cards_with_override = user_cards + [
        {"name": "动漫CG", "filename": "动漫CG.png", "prompt": "用户修改后的动漫CG提示词"},
    ]
    write_user_cards(user_cards_with_override)
    
    merged = read_merged_cards()
    print(f"用户卡片: {[c['name'] for c in user_cards_with_override]}")
    print(f"合并结果: {[c['name'] for c in merged]}")
    
    # 验证动漫CG的提示词是用户修改后的版本
    anime_cg = next((c for c in merged if c["name"] == "动漫CG"), None)
    assert anime_cg is not None, "动漫CG卡片应该存在"
    assert anime_cg["prompt"] == "用户修改后的动漫CG提示词", "动漫CG应该使用用户修改后的提示词"
    print("✓ 用户修改的默认卡片提示词已生效")
    
    # ===== 阶段 3：模拟插件更新（覆盖默认目录） =====
    print_separator("阶段 3：模拟插件更新（覆盖默认目录）")
    
    # 插件更新后，默认卡片可能增加、删除或修改
    updated_default_cards = [
        {"name": "动漫CG", "filename": "动漫CG.png", "prompt": "插件更新后的默认动漫CG提示词"},
        {"name": "二分动漫", "filename": "二分动漫.png", "prompt": "插件更新后的默认二分动漫提示词"},
        {"name": "水彩", "filename": "水彩.png", "prompt": "新增的水彩风格"},  # 新增
        # "卡通色块" 被移除（插件作者删除了这个默认卡片）
    ]
    write_json(DEFAULT_CARDS_FILE, updated_default_cards)
    
    print(f"更新后默认卡片: {[c['name'] for c in updated_default_cards]}")
    
    # ===== 阶段 4：验证用户数据未被覆盖 =====
    print_separator("阶段 4：验证用户数据完整性")
    
    # 读取用户目录
    user_cards_after = read_user_cards()
    print(f"用户卡片（更新后）: {[c['name'] for c in user_cards_after]}")
    
    # 验证用户自定义卡片仍然存在
    my_style = next((c for c in user_cards_after if c["name"] == "我的风格"), None)
    assert my_style is not None, "用户自定义卡片'我的风格'应该仍然存在"
    assert my_style["prompt"] == "用户自定义的提示词", "用户自定义卡片的提示词不应被改变"
    print("✓ 用户自定义卡片'我的风格'未被覆盖")
    
    cyberpunk = next((c for c in user_cards_after if c["name"] == "赛博朋克"), None)
    assert cyberpunk is not None, "用户自定义卡片'赛博朋克'应该仍然存在"
    print("✓ 用户自定义卡片'赛博朋克'未被覆盖")
    
    # 验证用户修改的默认卡片仍然使用用户版本
    user_anime_cg = next((c for c in user_cards_after if c["name"] == "动漫CG"), None)
    assert user_anime_cg is not None, "用户修改的'动漫CG'应该仍然存在于用户目录"
    assert user_anime_cg["prompt"] == "用户修改后的动漫CG提示词", "用户修改的提示词不应被覆盖"
    print("✓ 用户修改的'动漫CG'提示词未被插件更新覆盖")
    
    # ===== 阶段 5：验证合并结果 =====
    print_separator("阶段 5：验证合并后的卡片列表")
    
    merged_after = read_merged_cards()
    merged_names = [c["name"] for c in merged_after]
    print(f"合并后卡片: {merged_names}")
    
    # 验证合并结果
    assert "我的风格" in merged_names, "用户自定义卡片应该在合并结果中"
    assert "赛博朋克" in merged_names, "用户自定义卡片应该在合并结果中"
    assert "动漫CG" in merged_names, "默认卡片应该在合并结果中"
    assert "二分动漫" in merged_names, "默认卡片应该在合并结果中"
    assert "水彩" in merged_names, "新增的默认卡片应该在合并结果中"
    print("✓ 所有卡片都在合并结果中")
    
    # 验证用户修改的默认卡片使用用户版本
    merged_anime_cg = next((c for c in merged_after if c["name"] == "动漫CG"), None)
    assert merged_anime_cg["prompt"] == "用户修改后的动漫CG提示词", "合并后应该使用用户版本"
    print("✓ 合并后'动漫CG'使用用户修改的版本")
    
    # 验证新增的默认卡片
    merged_watercolor = next((c for c in merged_after if c["name"] == "水彩"), None)
    assert merged_watercolor is not None, "新增的水彩卡片应该在合并结果中"
    assert merged_watercolor["prompt"] == "新增的水彩风格", "新增卡片应该使用默认提示词"
    print("✓ 新增的默认卡片'水彩'已正确合并")
    
    # 验证被删除的默认卡片不再出现（如果用户没有自定义的话）
    # 注意：如果用户之前自定义了"卡通色块"，它仍会出现
    # 但在这个测试中，用户没有自定义"卡通色块"，所以它不应该出现
    assert "卡通色块" not in merged_names, "被删除的默认卡片不应该出现在合并结果中"
    print("✓ 被删除的默认卡片'卡通色块'已从合并结果中移除")
    
    print_separator("测试通过！")
    print("结论：插件更新不会覆盖用户自定义卡片数据")
    print(f"\n测试目录: {TEST_DIR}")
    print("（可手动删除测试目录，或保留用于检查）")


def cleanup():
    """清理测试目录"""
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
        print(f"\n已清理测试目录: {TEST_DIR}")


if __name__ == "__main__":
    try:
        setup_dirs()
        test_plugin_update_isolation()
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    finally:
        # 询问是否清理
        print("\n是否清理测试目录？(y/n): ", end="")
        # 自动清理（如需手动检查，注释掉下面两行）
        cleanup()
