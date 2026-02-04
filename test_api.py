#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek API 测试脚本
用于测试API密钥是否正确配置，以及API是否正常工作

使用方法：
    直接双击运行或: python test_api.py

注意：需要将API密钥填入 ds_api.txt 文件中
"""

import sys
import json


def test_deepseek_api(api_key: str):
    """测试DeepSeek API"""
    print("=" * 60)
    print("DeepSeek API 测试")
    print("=" * 60)
    
    if not api_key:
        print("错误: 未提供API密钥")
        print("请使用以下方式之一：")
        print("  1. 修改 ds_api.txt 文件，填入API密钥")
        print("  2. 运行: python test_api.py your-api-key")
        return False
    
    print(f"API密钥: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    # 导入urllib（Python内置，无需安装）
    import urllib.request
    import urllib.error
    
    url = "https://api.deepseek.com/v1/chat/completions"
    
    # 测试数据
    test_cases = [
        ("抽卡道具不足", "DRAW", "抽卡相关"),
        ("X{0}", "DRAW", "抽卡相关"),
        ("探索度{0}%", "DISCOVERY", "带参数"),
        ("等级{0}", "LEVEL", "等级相关"),
        ("战斗胜利", "BATTLE", "战斗相关"),
    ]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    success_count = 0
    fail_count = 0
    
    for chinese_text, context, description in test_cases:
        print(f"测试 [{description}]: {chinese_text}")
        
        prompt = f"""将以下中文翻译成C#常量命名风格（全部大写，下划线分隔，只返回翻译结果）：

中文: {chinese_text}
上下文: {context}

示例：抽卡道具不足 -> DRAW_CARD_ITEM_INSUFFICIENT"""

        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50,
            "temperature": 0.3
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if result.get("choices"):
                    translation = result["choices"][0]["message"]["content"].strip()
                    print(f"  翻译结果: {translation}")
                    success_count += 1
                else:
                    print(f"  API返回格式错误")
                    fail_count += 1
                    
        except urllib.error.HTTPError as e:
            print(f"  HTTP错误: {e.code}")
            if e.code == 401:
                print("     原因: API密钥无效")
            elif e.code == 429:
                print("     原因: 请求频率超限")
            fail_count += 1
        except urllib.error.URLError as e:
            print(f"  网络错误: {e.reason}")
            fail_count += 1
        except Exception as e:
            print(f"  未知错误: {e}")
            fail_count += 1
        
        print()
    
    # 总结
    print("=" * 60)
    print(f"测试结果: {success_count} 成功, {fail_count} 失败")
    print("=" * 60)
    
    if fail_count == 0:
        print("所有测试通过！API配置正确")
        return True
    else:
        print("部分测试失败，请检查API密钥和网络连接")
        return False


def main():
    """主函数"""
    import os
    
    # 尝试从 ds_api.txt 读取
    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_key_file = os.path.join(script_dir, 'ds_api.txt')
    
    api_key = None
    if os.path.exists(api_key_file):
        print(f"从 ds_api.txt 读取API密钥")
        try:
            with open(api_key_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        api_key = line
                        break
        except Exception as e:
            print(f"读取 ds_api.txt 失败: {e}")
    
    # 运行测试
    test_deepseek_api(api_key)


if __name__ == '__main__':
    main()
