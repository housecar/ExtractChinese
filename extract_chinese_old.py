#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文字符串提取工具
用于从C#代码中提取中文字符串并生成多语言表格

支持两种模式：
1. all: 扫描目录下所有子文件夹，每个子文件夹生成一个csv
2. single: 扫描单个目录，生成一个csv

Usage:
    python extract_chinese.py --mode all --path "D:\\project\\MJZ2_Client\\trunk\\MJZ2\\Assets\\Scripts\\Game\\Module\\Function"
    python extract_chinese.py --mode single --path "D:\\project\\MJZ2_Client\\trunk\\MJZ2\\Assets\\Scripts\\Game\\Module\\Function\\Battle"
    python extract_chinese.py --mode all --path "D:\\project\\MJZ2_Client\\trunk\\MJZ2\\Assets\\Scripts\\Game\\Module\\Function" --api-key "your-deepseek-api-key"
"""

import os
import re
import argparse
import csv
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import sys


@dataclass
class ChineseString:
    """中文字符串信息"""
    value: str  # 原始中文文本（参数已替换为{0},{1}等）
    original_value: str  # 原始中文文本（带参数名）
    pos: str  # 位置信息 (文件路径---行数)
    file_path: str
    line_number: int


class TranslationCache:
    """翻译缓存，用于减少API调用"""
    def __init__(self, cache_file: str = "translation_cache.json"):
        self.cache_file = cache_file
        self.cache: Dict[str, str] = self._load_cache()
    
    def _load_cache(self) -> Dict[str, str]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def get(self, key: str) -> Optional[str]:
        return self.cache.get(key)
    
    def set(self, key: str, value: str):
        self.cache[key] = value


class DeepSeekTranslator:
    """DeepSeek API翻译器"""
    
    def __init__(self, api_key: str, cache: TranslationCache):
        self.api_key = api_key
        self.cache = cache
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
    
    def translate(self, chinese_text: str, context: str = "") -> str:
        """
        将中文翻译成英文变量名
        例如: "抽卡道具不足" -> "DRAW_DRAW_ITEM_INSUFFICIENT"
        """
        # 先检查缓存
        cache_key = f"{context}:{chinese_text}" if context else chinese_text
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # 构建提示
        prompt = self._build_prompt(chinese_text, context)
        
        try:
            result = self._call_api(prompt)
            if result:
                self.cache.set(cache_key, result)
                return result
        except Exception as e:
            print(f"翻译API调用失败: {e}")
        
        # 如果API调用失败，使用本地翻译
        result = self._local_translate(chinese_text)
        self.cache.set(cache_key, result)
        return result
    
    def _build_prompt(self, chinese_text: str, context: str = "") -> str:
        return f"""请将以下中文文本翻译成C#常量命名风格（使用下划线分隔大写字母，格式如：DRAW_DRAW_ITEM_INSUFFICIENT）

中文文本: {chinese_text}
上下文（文件夹名称）: {context}

要求：
1. 全部使用大写字母
2. 使用下划线分隔单词
3. 保持简洁但要有描述性
4. 只返回翻译结果，不要其他内容
5. 不要包含中文

示例：
- "抽卡道具不足" -> "DRAW_DRAW_ITEM_INSUFFICIENT"
- "再结义 {{0}} 次必得红将" -> "DRAW_RED_GENERAL_GUARANTEED"

请翻译: {chinese_text}"""
    
    def _call_api(self, prompt: str) -> Optional[str]:
        """调用DeepSeek API"""
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 100,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            if result.get("choices"):
                return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"API错误: {e}")
        return None
    
    def _local_translate(self, chinese_text: str) -> str:
        """本地翻译（当API不可用时使用）"""
        # 移除参数占位符
        text = re.sub(r'\{[\w\s]+\}', '', chinese_text)
        # 简单的翻译逻辑
        words = []
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                words.append(char)
        
        if not words:
            return "UNKNOWN"
        
        # 使用简单的翻译
        result = "_".join([self._char_to_pinyin(c) for c in words[:5]])
        return result.upper()[:50]
    
    def _char_to_pinyin(self, char: str) -> str:
        """简单的中文字符转拼音"""
        pinyin_map = {
            '抽': 'DRAW', '卡': 'CARD', '道': 'ITEM', '具': 'PROP', '不': 'NOT',
            '足': 'SUFFICIENT', '再': 'RE', '结': 'BIND', '义': 'YI', '次': 'TIME',
            '必': 'MUST', '得': 'GET', '红': 'RED', '将': 'GENERAL', '累': 'CUMULATIVE',
            '计': 'COUNT', '总': 'TOTAL', '资': 'RESOURCE', '源': 'SOURCE', '提': 'EXTRACT',
            '示': 'SHOW', '确': 'CONFIRM', '认': 'CONFIRM', '取': 'GET', '消': 'CANCEL',
            '完': 'COMPLETE', '成': 'COMPLETE', '错': 'ERROR', '误': 'ERROR', '失': 'FAIL',
            '败': 'FAIL', '成': 'SUCCESS', '功': 'SUCCESS', '请': 'PLEASE', '求': 'REQUEST',
            '加': 'ADD', '载': 'LOAD', '时': 'TIME', '间': 'TIME', '限': 'LIMIT',
            '拖': 'DRAG', '拽': 'DROP', '物': 'ITEM', '品': 'PRODUCT', '数': 'COUNT',
            '量': 'AMOUNT', '无': 'NO', '法': 'WAY', '操': 'OPERATE', '作': 'ACTION',
            '确': 'CONFIRM', '定': 'DEFINE', '购': 'PURCHASE', '买': 'BUY', '这': 'THIS',
            '个': 'GE', '吗': 'QUESTION', '恭': 'CONGRATULATE', '喜': 'JOY', '获': 'GET',
            '奖': 'REWARD', '励': 'INCENTIVE', '方': 'DIRECTION', '单': 'SINGLE', '位': 'UNIT',
            '敌': 'ENEMY', '还': 'STILL', '有': 'HAVE', '胜': 'VICTORY', '利': 'PROFIT',
            '准': 'PREPARE', '备': 'PREPARE', '开': 'START', '始': 'BEGIN', '始': 'BEGIN',
        }
        return pinyin_map.get(char, 'CN')


class ChineseExtractor:
    """中文字符串提取器"""
    
    # 需要忽略的文件夹模式
    IGNORE_FOLDER_PATTERNS = [
        re.compile(r'.*Bind.*', re.IGNORECASE),  # 包含Bind的文件夹
        re.compile(r'.*\.git.*'),
        re.compile(r'.*\.svn.*'),
        re.compile(r'.*node_modules.*'),
        re.compile(r'.*__pycache__.*'),
        re.compile(r'.*\.vscode.*'),
        re.compile(r'.*\.idea.*'),
    ]
    
    # 需要忽略的API模式
    IGNORE_API_PATTERNS = [
        # Debug日志相关
        re.compile(r'Debug\.(Log|LogError|LogWarning|LogFormat|LogException)'),
        re.compile(r'SLApp\.Log\.(Info|Warning|Error)'),
        re.compile(r'SLApp\.Debug\.(Log|LogFormat|LogError|LogWatchBegin|LogWatchEnd)'),
        re.compile(r'UnityEngine\.Debug\.'),
        re.compile(r'Console\.WriteLine'),
        re.compile(r'UnityEditor\.EditorUtility\.DisplayDialog'),
        
        # 异常抛出相关 - 忽略 throw new Exception("...") 中的中文
        re.compile(r'throw\s+new\s+(?:System\.)?(?:Exception|NullReferenceException|ArgumentNullException|ArgumentException|IndexOutOfRangeException|InvalidOperationException|NotImplementedException|UnauthorizedAccessException|KeyNotFoundException|DivideByZeroException|OverflowException|FormatException|TimeoutException|IOException|DirectoryNotFoundException|FileNotFoundException|PathTooLongException)\s*\([^)]*\)'),
        
        # 异常日志记录
        re.compile(r'\.LogException\s*\('),
        re.compile(r'\.LogErrorException\s*\('),
        re.compile(r'ExceptionHelper\.'),
    ]
    
    # 代码文件扩展名
    # CODE_EXTENSIONS = {'.cs', '.ts', '.js', '.jsx', '.vue', '.py', '.java', '.cpp', '.c', '.h'}
    CODE_EXTENSIONS = {'.cs',}
    
    def __init__(self, translator: Optional[DeepSeekTranslator] = None):
        self.translator = translator
    
    def should_skip_file(self, file_path: str) -> bool:
        """检查是否应该跳过该文件"""
        # 检查文件夹模式
        path_parts = file_path.split(os.sep)
        for part in path_parts:
            for pattern in self.IGNORE_FOLDER_PATTERNS:
                if pattern.match(part):
                    return True
        return False
    
    def extract_from_file(self, file_path: str) -> List[ChineseString]:
        """从单个文件中提取中文字符串"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return results
        
        lines = content.split('\n')
        
        # 预处理：标记注释区域
        in_multiline_comment = False
        in_header_attribute = False
        
        for i, line in enumerate(lines, 1):
            original_line = line
            
            # 移除行尾注释（但保留字符串）
            line_without_comment = self._remove_comment_from_line(line)
            
            # 检查多行注释
            if '/*' in line:
                in_multiline_comment = True
            if '*/' in line:
                in_multiline_comment = False
            
            # 跳过注释区域
            if in_multiline_comment:
                continue
            
            # 检查并跳过Attribute声明（如[Header("...")]、[Tooltip("...")]等）
            if self._is_attribute_declaration(line):
                continue
            
            # 在原始行中查找中文字符串
            chinese_strings = self._find_chinese_strings(original_line)
            
            for chinese_text in chinese_strings:
                formatted = self._format_string(chinese_text)
                pos = f"{os.path.basename(file_path)}---{i}"
                
                results.append(ChineseString(
                    value=formatted,
                    original_value=chinese_text,
                    pos=pos,
                    file_path=file_path,
                    line_number=i
                ))
        
        return results
    
    def _remove_comment_from_line(self, line: str) -> str:
        """移除行尾注释，保留字符串"""
        # 找到字符串开始的位置（不是转义的引号）
        result = []
        in_string = False
        string_char = None
        
        for char in line:
            if not in_string and (char == '"' or char == "'"):
                in_string = True
                string_char = char
                result.append(char)
            elif in_string and char == string_char:
                # 检查是否是转义的引号
                if result and result[-1] == '\\':
                    result[-1] = char
                else:
                    in_string = False
                    string_char = None
                    result.append(char)
            elif not in_string and char == '/':
                # 检查是否是注释开始
                if result and result[-1] == '/':
                    result.pop()  # 移除第一个/
                    break  # 后面都是注释
                else:
                    result.append(char)
            else:
                result.append(char)
        
        return ''.join(result)
    
    def _is_attribute_declaration(self, line: str) -> bool:
        """
        检查是否是Attribute声明行
        例如：[Header("...")]、[Tooltip("...")]、[Description("...")] 等
        规则：忽略所有Attribute声明中的中文
        """
        stripped = line.strip()
        
        # 检查是否以 [ 开头且包含 ]
        # 并且整行就是一个Attribute声明（没有其他代码）
        if stripped.startswith('[') and ']' in stripped:
            # 获取 ] 之后的内容
            bracket_end = stripped.find(']')
            after_bracket = stripped[bracket_end + 1:].strip()
            
            # 如果 ] 后面没有其他代码，说明是纯Attribute声明
            if not after_bracket:
                return True
            
            # 检查是否是字段/属性声明开头的行
            # 例如：public int count; [Tooltip("xxx")] 这种情况不应该跳过
            if re.match(r'^\w+\s+\w+.*;?\s*$', after_bracket):
                return False
            
            # 其他情况视为纯Attribute声明
            return True
        
        return False
    
    def _find_chinese_strings(self, line: str) -> List[str]:
        """在行中查找中文字符串
        
        注意：对于插值字符串 $"..."，无论是否包含中文，
        只要字符串内容不为空，就会被记录
        """
        results = []
        
        # 忽略Debug相关API
        for pattern in self.IGNORE_API_PATTERNS:
            if pattern.search(line):
                return []
        
        # 处理插值字符串 $"..." 
        # 注意：先处理插值字符串，再处理普通字符串
        interpolated_matches = re.findall(r'\$\"([^\"]*)\"', line)
        for match in interpolated_matches:
            # 插值字符串：如果包含中文，或者包含参数占位符，都应该记录
            if self._contains_chinese(match) or self._has_parameters(match):
                results.append(match)
        
        # 处理普通字符串 "..."
        string_matches = re.findall(r'\"([^\"]*)\"', line)
        for match in string_matches:
            if self._contains_chinese(match):
                # 避免重复添加已经在插值字符串中找到的内容
                if match not in results:
                    results.append(match)
        
        return results
    
    def _has_parameters(self, text: str) -> bool:
        """检查是否包含参数占位符 {xxx}"""
        return bool(re.search(r'\{(?:[^{}]|\{[^{}]*\})+\}', text))
    
    def _contains_chinese(self, text: str) -> bool:
        """检查是否包含中文字符"""
        return bool(re.search('[\u4e00-\u9fff]', text))
    
    def _format_string(self, text: str) -> str:
        """格式化字符串，将参数替换为 {0}, {1} 等
        
        支持以下情况：
        - 简单变量: {monster_level} -> {0}
        - 属性访问: {_levelCfg.monster_level} -> {0}
        - 方法调用: {NumberUtils.FormatNumber(fake_power)} -> {0}
        - 长度属性: {monster_id.Length} -> {0}
        """
        # 找到所有 {xxx} 或 {...} 形式的参数占位符
        # 使用 \{[^}]+\} 匹配 { 后面跟着非 } 字符，直到 }
        param_pattern = r'\{[^}]+\}'
        
        # 找到所有参数占位符
        params = re.findall(param_pattern, text)
        
        if not params:
            return text
        
        # 替换为 {0}, {1}, {2}...
        result = text
        for i, param in enumerate(params):
            # 只替换第一个匹配，确保按顺序
            result = result.replace(param, '{' + str(i) + '}', 1)
        
        return result
    
    def extract_from_directory(self, dir_path: str) -> Dict[str, List[ChineseString]]:
        """从目录中提取所有中文字符串"""
        results = {}
        
        for root, dirs, files in os.walk(dir_path):
            # 过滤掉需要忽略的文件夹
            dirs[:] = [d for d in dirs if not self.should_skip_file(os.path.join(root, d))]
            
            for file in files:
                if Path(file).suffix not in self.CODE_EXTENSIONS:
                    continue
                
                file_path = os.path.join(root, file)
                
                if self.should_skip_file(file_path):
                    continue
                
                strings = self.extract_from_file(file_path)
                
                if strings:
                    # 按文件夹分组
                    relative_path = os.path.relpath(file_path, dir_path)
                    folder = os.path.dirname(relative_path)
                    if folder == '.':
                        folder = os.path.basename(dir_path)
                    
                    if folder not in results:
                        results[folder] = []
                    
                    results[folder].extend(strings)
        
        return results


class CSVGenerator:
    """CSV文件生成器"""
    
    def __init__(self, translator: Optional[DeepSeekTranslator] = None):
        self.translator = translator
    
    def generate_key(self, chinese_text: str, context: str = "") -> str:
        """生成变量名key"""
        if self.translator:
            return self.translator.translate(chinese_text, context)
        else:
            # 使用默认翻译
            return self._default_key_translate(chinese_text)
    
    def _default_key_translate(self, chinese_text: str) -> str:
        """默认的key翻译逻辑"""
        # 清理参数占位符 {0}, {1} 等
        text = re.sub(r'\{[\d]+\}', '', chinese_text)
        text = text.strip()
        
        if not text:
            return "EMPTY_STRING"
        
        # 使用简单的字符映射
        words = []
        for char in text[:10]:  # 限制长度
            if '\u4e00' <= char <= '\u9fff':
                words.append(char)
        
        if not words:
            return "UNKNOWN"
        
        return "_".join(words).upper()
    
    def generate_csv(self, strings: List[ChineseString], output_path: str, context: str = ""):
        """生成CSV文件"""
        # 去重（基于格式化后的value）
        unique_data = {}
        for s in strings:
            key = s.value
            if key not in unique_data:
                unique_data[key] = s
        
        # 生成数据
        data_rows = []
        for value, cs in unique_data.items():
            key = self.generate_key(value, context)
            data_rows.append({
                'key': key,
                'value': value,
                'pos': cs.pos
            })
        
        # 写入CSV
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['key', 'value', 'pos'])
            writer.writeheader()
            writer.writerows(data_rows)
        
        print(f"已生成: {output_path} (共 {len(data_rows)} 条)")


def main():
    parser = argparse.ArgumentParser(description='中文字符串提取工具')
    parser.add_argument('--mode', choices=['all', 'single'], required=True,
                        help='提取模式: all=扫描所有子文件夹, single=扫描单个目录')
    parser.add_argument('--path', required=True, help='扫描路径')
    parser.add_argument('--api-key', default=None, help='DeepSeek API密钥（默认从ds_api.txt读取）')
    parser.add_argument('--output-dir', default=None, help='输出目录（可选）')
    
    args = parser.parse_args()
    
    dir_path = args.path
    if not os.path.exists(dir_path):
        print(f"错误: 路径不存在 {dir_path}")
        sys.exit(1)
    
    # 初始化翻译器和缓存
    cache = TranslationCache()
    translator = None
    
    # 获取API密钥：优先使用命令行参数，其次使用ds_api.txt文件
    api_key = args.api_key
    if not api_key:
        # 尝试从脚本同目录下的ds_api.txt读取
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_key_file = os.path.join(script_dir, 'ds_api.txt')
        
        if os.path.exists(api_key_file):
            try:
                with open(api_key_file, 'r', encoding='utf-8') as f:
                    file_content = f.read().strip()
                    # 读取第一行作为API密钥
                    lines = file_content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            api_key = line
                            break
                
                if api_key:
                    print(f"✓ 已从 ds_api.txt 读取API密钥")
                else:
                    print("⚠ ds_api.txt 文件内容为空，将不使用DeepSeek翻译")
            except Exception as e:
                print(f"⚠ 读取 ds_api.txt 失败: {e}，将不使用DeepSeek翻译")
        else:
            print("ℹ 未提供 --api-key 参数，且 ds_api.txt 文件不存在，将不使用DeepSeek翻译")
    
    # 如果有API密钥，初始化翻译器
    if api_key:
        translator = DeepSeekTranslator(api_key, cache)
        print("✓ DeepSeek翻译功能已启用")
    
    extractor = ChineseExtractor(translator)
    csv_generator = CSVGenerator(translator)
    
    if args.mode == 'all':
        # 扫描所有子文件夹
        # 输出到输入路径的根目录
        output_base = args.output_dir or dir_path
        
        # 遍历输入路径下的所有子文件夹
        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            if os.path.isdir(item_path):
                # 跳过忽略的文件夹
                if extractor.should_skip_file(item_path):
                    continue
                
                print(f"\n扫描文件夹: {item}")
                results = extractor.extract_from_directory(item_path)
                
                if results:
                    # 生成CSV文件名（使用子文件夹名称）
                    csv_name = item
                    
                    # 确保是有效的文件名
                    csv_name = re.sub(r'[<>:"/\\|?*]', '_', csv_name)
                    output_path = os.path.join(output_base, f"{csv_name}.csv")
                    
                    # 合并所有字符串
                    all_strings = []
                    for folder, strings in results.items():
                        all_strings.extend(strings)
                    
                    # 生成CSV
                    csv_generator.generate_csv(all_strings, output_path, context=item)
                else:
                    print(f"  文件夹 {item} 中没有找到中文字符串")
    
    elif args.mode == 'single':
        # 只扫描单个目录
        # 获取输入路径的最后一个文件夹名作为CSV名字
        folder_name = os.path.basename(dir_path)
        
        # 输出到输入路径的父目录
        output_base = args.output_dir or os.path.dirname(dir_path)
        
        print(f"\n扫描目录: {dir_path}")
        results = extractor.extract_from_directory(dir_path)
        
        if results:
            # 生成CSV文件
            csv_name = folder_name
            csv_name = re.sub(r'[<>:"/\\|?*]', '_', csv_name)
            output_path = os.path.join(output_base, f"{csv_name}.csv")
            
            # 合并所有字符串
            all_strings = []
            for folder, strings in results.items():
                all_strings.extend(strings)
            
            csv_generator.generate_csv(all_strings, output_path, context=folder_name)
    
    # 保存翻译缓存
    cache.save()
    print("\n提取完成！")
    print(f"翻译缓存已保存到: {cache.cache_file}")


if __name__ == '__main__':
    main()
