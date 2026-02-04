#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文字符串提取工具
用于从C#代码中提取中文字符串并生成多语言表格

使用方式：
    python extract_chinese.py all              # 扫描Function下所有子文件夹
    python extract_chinese.py single Battle    # 扫描Function下的Battle文件夹

配置文件：
    ds_api.txt - 存放DeepSeek API密钥（可选）
"""

import os
import re
import csv
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


# ==================== 配置 ====================
# 脚本所在目录
SCRIPT_DIR = Path(__file__).parent.resolve()

# 代码模块根目录（相对于脚本目录或绝对路径）
CODE_MODULE_DIR = SCRIPT_DIR.parent.parent / "Assets" / "Scripts" / "Game" / "Module" / "Function"

# 输出目录
OUTPUT_DIR = SCRIPT_DIR / "csv"

# 缓存文件
CACHE_FILE = SCRIPT_DIR / "translation_cache.json"

# API密钥文件
API_KEY_FILE = SCRIPT_DIR / "ds_api.txt"


@dataclass
class ChineseString:
    """中文字符串信息"""
    value: str  # 格式化后的中文文本（参数已替换为{0},{1}等）
    pos: str    # 位置信息 (文件名---行数)


class TranslationCache:
    """翻译缓存"""
    
    def __init__(self):
        self.cache: Dict[str, str] = {}
        self._load_cache()
    
    def _load_cache(self):
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except:
                self.cache = {}
    
    def save(self):
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
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
        """将中文翻译成英文变量名"""
        cache_key = f"{context}:{chinese_text}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # 本地翻译优先（避免API调用问题）
        result = self._local_translate(chinese_text, context)
        
        # 尝试API翻译
        try:
            api_result = self._call_api(chinese_text, context)
            if api_result and api_result != result:
                result = api_result
                self.cache.set(cache_key, result)
                return result
        except Exception as e:
            print(f"  翻译API调用失败: {e}")
        
        self.cache.set(cache_key, result)
        return result
    
    def _call_api(self, chinese_text: str, context: str) -> Optional[str]:
        """调用DeepSeek API"""
        import urllib.request
        import urllib.error
        import json
        
        prompt = f"""将以下中文翻译成C#常量命名风格（全部大写，下划线分隔）：

中文: {chinese_text}
上下文: {context}

只返回翻译结果，不要其他内容。
示例：抽卡道具不足 -> DRAW_DARD_ITEM_INSUFFICIENT"""

        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50,
            "temperature": 0.3
        }
        
        try:
            req = urllib.request.Request(
                self.api_url,
                data=json.dumps(data).encode('utf-8'),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get("choices"):
                    return result["choices"][0]["message"]["content"].strip()
        except Exception:
            pass
        
        return None
    
    def _local_translate(self, chinese_text: str, context: str) -> str:
        """本地翻译"""
        # 清理参数占位符
        text = re.sub(r'\{[\d]+\}', '', chinese_text).strip()
        
        if not text:
            # 只有参数的情况，使用上下文+参数数量生成key
            param_count = len(re.findall(r'\{[\d]+\}', chinese_text))
            if context:
                return f"{context.upper()}_PARAM_{param_count}"
            return f"PARAM_{param_count}"
        
        # 常用词汇映射（扩展版）
        word_map = {
            # 抽卡相关
            '抽': 'DRAW', '卡': 'CARD', '道': 'ITEM', '具': 'PROP',
            '足': 'SUFFICIENT', '不': 'NOT', '再': 'RE', '结': 'OATH',
            '义': 'BIND', '次': 'TIME', '必': 'MUST', '得': 'GET',
            '红': 'RED', '将': 'GENERAL', '累': 'TOTAL', '计': 'COUNT',
            '总': 'TOTAL', '资': 'RESOURCE', '源': 'SOURCE',
            
            # 通用UI
            '确': 'CONFIRM', '认': 'CONFIRM', '购': 'PURCHASE',
            '买': 'BUY', '这': 'THIS', '个': 'GE', '吗': 'QUESTION',
            '请': 'PLEASE', '拖': 'DRAG', '拽': 'DROP', '指': 'SPECIFY',
            '定': 'FIXED', '位': 'POSITION', '物': 'ITEM',
            '品': 'PRODUCT', '数': 'NUMBER', '量': 'AMOUNT',
            '无': 'NO', '法': 'WAY', '完': 'COMPLETE', '成': 'COMPLETE',
            
            # 探索/关卡相关
            '探': 'EXPLORE', '索': 'SEARCH', '度': 'DEGREE',
            '推': 'RECOMMEND', '荐': 'RECOMMEND', '战': 'BATTLE',
            '力': 'POWER', '等': 'LEVEL', '阵': 'LINEUP',
            '容': 'CONTAINER', '为': 'IS', '空': 'EMPTY',
            '无': 'CANNOT', '法': 'ABLE', '跳': 'JUMP', '过': 'PASS',
            '主': 'MAIN', '线': 'LINE', '关': 'LEVEL', '尚': 'NOT',
            '未': 'UN', '解': 'UNLOCK', '锁': 'LOCK',
            
            # 路径/地图相关
            '路': 'PATH', '径': 'WAY', '点': 'POINT',
            '错': 'ERROR', '误': 'ERROR', '需': 'NEED',
            '地': 'MAP', '图': 'MAP', '资': 'ASSET',
            '产': 'ASSET', '态': 'STATE', '信': 'INFO',
            '息': 'TION', '显': 'SHOW', '示': 'SHOW',
            
            # 奖励/任务
            '奖': 'REWARD', '励': 'INCENTIVE', '务': 'TASK',
            '完': 'COMPLETE', '败': 'FAIL', '功': 'SUCCESS',
            
            # 操作相关
            '返': 'BACK', '回': 'RETURN', '关': 'CLOSE',
            '闭': 'CLOSE', '打': 'OPEN', '开': 'OPEN',
            '设': 'SET', '置': 'TING', '选': 'OPTION',
            '项': 'ITEM', '提': 'TIP', '警': 'WARNING',
            '告': 'ALERT', '可': 'CAN', '以': 'ABLE',
            '任': 'APPOINT', '命': 'NAME', '州': 'STATE',
            '牧': 'GOVERNOR', '获': 'GET', '得': 'OBTAIN',
            '额': 'EXTRA', '外': 'EXTRA', '占': 'OCCUPY',
            '领': 'LEAD', '产': 'OUTPUT', '出': 'OUTPUT',
            '加': 'BONUS', '成': 'cheng',
        }
        
        # 翻译每个字符
        result_words = []
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                translated = word_map.get(char, char)
                # 如果翻译结果还是中文字符，跳过
                if '\u4e00' <= translated <= '\u9fff':
                    continue
                result_words.append(translated)
        
        if not result_words:
            # 没有可翻译的字符，使用上下文+描述
            param_count = len(re.findall(r'\{[\d]+\}', chinese_text))
            if param_count > 0:
                return f"{context.upper()}_PARAM_{param_count}"
            return f"{context.upper()}_TEXT"
        
        # 生成key，确保以模块名开头
        module_name = context.upper() if context else ""
        result = "_".join(result_words)
        
        # 限制长度（减去模块名和下划线的长度）
        max_len = 50 - len(module_name) - 1
        if max_len > 0:
            result = result[:max_len]
        
        return f"{module_name}_{result}" if module_name else result


class ChineseExtractor:
    """中文字符串提取器"""
    
    # 需要忽略的文件夹
    IGNORE_FOLDERS = {'bind', 'Bind', 'BIND', '.git', '.svn', 'node_modules'}
    
    # 需要忽略的API
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
    CODE_EXTENSIONS = {'.cs'}
    
    def extract_from_file(self, file_path: Path) -> List[ChineseString]:
        """从文件中提取中文字符串"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  读取失败: {e}")
            return results
        
        lines = content.split('\n')
        in_multiline_comment = False
        
        for i, line in enumerate(lines, 1):
            original_line = line
            
            # 检查多行注释
            if '/*' in line:
                in_multiline_comment = True
            if '*/' in line:
                in_multiline_comment = False
                continue
            
            if in_multiline_comment:
                continue
            
            # 检查Attribute
            if self._is_attribute_line(line):
                continue
            
            # 移除行尾注释
            line = self._remove_comment(line)
            
            # 忽略Debug API
            for pattern in self.IGNORE_API_PATTERNS:
                if pattern.search(original_line):
                    continue
            
            # 查找字符串
            chinese_strings = self._find_chinese_strings(original_line)
            
            for text in chinese_strings:
                formatted = self._format_string(text)
                pos = f"{file_path.name}---{i}"
                
                results.append(ChineseString(
                    value=formatted,
                    pos=pos
                ))
        
        return results
    
    def _is_attribute_line(self, line: str) -> bool:
        """检查是否是纯Attribute行"""
        stripped = line.strip()
        if stripped.startswith('[') and ']' in stripped:
            bracket_end = stripped.find(']')
            after_bracket = stripped[bracket_end + 1:].strip()
            if not after_bracket:
                return True
        return False
    
    def _remove_comment(self, line: str) -> str:
        """移除行尾注释"""
        result = []
        in_string = False
        string_char = None
        
        for char in line:
            if not in_string and (char == '"' or char == "'"):
                in_string = True
                string_char = char
                result.append(char)
            elif in_string and char == string_char:
                if result and result[-1] == '\\':
                    result[-1] = char
                else:
                    in_string = False
                    string_char = None
                    result.append(char)
            elif not in_string and char == '/' and result and result[-1] == '/':
                break
            else:
                result.append(char)
        
        return ''.join(result)
    
    def _find_chinese_strings(self, line: str) -> List[str]:
        """查找中文字符串"""
        # 首先检查是否包含忽略的API
        for pattern in self.IGNORE_API_PATTERNS:
            if pattern.search(line):
                return []
        
        results = []
        
        # 插值字符串 $"" 
        for match in re.findall(r'\$\"([^\"]*)\"', line):
            if self._has_chinese(match) or self._has_params(match):
                results.append(match)
        
        # 普通字符串 ""
        for match in re.findall(r'\"([^\"]*)\"', line):
            if self._has_chinese(match) and match not in results:
                results.append(match)
        
        return results
    
    def _has_chinese(self, text: str) -> bool:
        return bool(re.search('[\u4e00-\u9fff]', text))
    
    def _has_params(self, text: str) -> bool:
        return bool(re.search(r'\{[^}]+\}', text))
    
    def _format_string(self, text: str) -> str:
        """格式化字符串，参数替换为{0},{1}..."""
        params = re.findall(r'\{[^}]+\}', text)
        result = text
        for i, param in enumerate(params):
            result = result.replace(param, '{' + str(i) + '}', 1)
        return result
    
    def extract_from_directory(self, dir_path: Path) -> List[ChineseString]:
        """从目录中提取所有中文字符串"""
        results = []
        
        for root, dirs, files in os.walk(dir_path):
            # 过滤忽略的文件夹
            dirs[:] = [d for d in dirs if d not in self.IGNORE_FOLDERS]
            
            for file in files:
                if Path(file).suffix not in self.CODE_EXTENSIONS:
                    continue
                
                file_path = Path(root) / file
                strings = self.extract_from_file(file_path)
                results.extend(strings)
        
        return results


class CSVGenerator:
    """CSV生成器"""
    
    def __init__(self, translator: Optional[DeepSeekTranslator]):
        self.translator = translator
    
    def generate(self, strings: List[ChineseString], output_path: Path, context: str = ""):
        """生成CSV文件"""
        if not strings:
            print(f"  没有找到中文字符串")
            return
        
        # 去重
        unique_data = {}
        for s in strings:
            if s.value not in unique_data:
                unique_data[s.value] = s
        
        # 生成数据
        data_rows = []
        for value, cs in unique_data.items():
            if self.translator:
                key = self.translator.translate(value, context)
            else:
                key = self._default_key(value, context)
            
            # 确保key以模块名开头
            if context:
                module_prefix = context.upper() + "_"
                if not key.startswith(module_prefix):
                    key = module_prefix + key
            
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
        
        print(f"  ✓ 已生成: {output_path.name} ({len(data_rows)} 条)")
    
    def _default_key(self, text: str, context: str) -> str:
        """默认key生成 - 确保以模块名开头"""
        module_name = context.upper() if context else ""
        
        clean_text = re.sub(r'\{[\d]+\}', '', text).strip()
        
        if not clean_text:
            # 只有参数的情况
            param_count = len(re.findall(r'\{[\d]+\}', text))
            return f"{module_name}_PARAM_{param_count}" if module_name else f"PARAM_{param_count}"
        
        # 简单翻译
        word_map = {
            '探索': 'EXPLORE', '度': 'DEGREE', '推荐': 'RECOMMEND', '战力': 'POWER',
            '等级': 'LEVEL', '阵容': 'LINEUP', '为空': 'EMPTY', '无法': 'CANNOT',
            '跳过': 'SKIP', '主线': 'MAINLINE', '关卡': 'LEVEL', '尚未': 'NOT',
            '解锁': 'UNLOCK', '路径': 'PATH', '点': 'POINT', '数量': 'COUNT',
            '错误': 'ERROR', '总': 'TOTAL', '需': 'NEED', '地图': 'MAP',
            '资产': 'ASSET', '状态': 'STATE', '信息': 'INFO', '显示': 'SHOW',
            '奖励': 'REWARD', '任务': 'TASK', '完成': 'COMPLETE', '失败': 'FAIL',
            '成功': 'SUCCESS', '确认': 'CONFIRM', '取消': 'CANCEL', '返回': 'BACK',
            '关闭': 'CLOSE', '打开': 'OPEN', '设置': 'SETTING', '选项': 'OPTION',
            '提示': 'TIP', '警告': 'WARNING', '错误': 'ERROR', '可以': 'CAN',
            '任命': 'APPOINT', '州牧': 'GOVERNOR', '获得': 'GET', '额外': 'EXTRA',
            '占领': 'OCCUPY', '产出': 'OUTPUT', '加成': 'BONUS',
            '抽': 'DRAW', '卡': 'CARD', '道': 'ITEM', '具': 'PROP',
            '足': 'SUFFICIENT', '次': 'TIME', '必': 'MUST', '得': 'GET',
            '红': 'RED', '将': 'GENERAL', '累': 'TOTAL', '计': 'COUNT',
            '确': 'CONFIRM', '认': 'CONFIRM', '购': 'PURCHASE', '买': 'BUY',
            '请': 'PLEASE', '拖': 'DRAG', '拽': 'DROP', '指': 'SPECIFY',
            '位': 'POSITION', '物': 'ITEM', '品': 'PRODUCT', '数': 'NUMBER',
            '量': 'AMOUNT', '无': 'NO', '法': 'WAY', '完': 'COMPLETE',
            '敌': 'ENEMY', '方': 'SIDE', '还': 'STILL', '有': 'HAVE',
            '单': 'SINGLE', '位': 'UNIT', '战': 'BATTLE', '斗': 'FIGHT',
            '胜': 'VICTORY', '利': 'PROFIT', '奖': 'REWARD', '励': 'BONUS',
            '准': 'PREPARE', '备': 'READY', '开': 'START', '始': 'BEGIN',
            '恭': 'CONGRATULATE', '喜': 'JOY', '获': 'GET',
        }
        
        words = []
        for char in clean_text:
            if '\u4e00' <= char <= '\u9fff':
                words.append(word_map.get(char, char))
        
        if not words:
            return f"{module_name}_TEXT" if module_name else "TEXT"
        
        # 确保以模块名开头
        result = "_".join(words)
        
        # 限制长度（减去模块名和下划线的长度）
        max_len = 50 - len(module_name) - 1
        if max_len > 0:
            result = result[:max_len]
        
        return f"{module_name}_{result}" if module_name else result


def get_api_key() -> Optional[str]:
    """获取API密钥"""
    # 检查命令行参数（需要 argparse）
    pass


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='中文字符串提取工具')
    parser.add_argument('mode', choices=['all', 'single'], help='提取模式')
    parser.add_argument('folder', nargs='?', default=None, help='文件夹名（single模式需要）')
    parser.add_argument('--api-key', dest='api_key', default=None, help='DeepSeek API密钥')
    parser.add_argument('--code-path', dest='code_path', default=None, help='代码模块路径')
    
    args = parser.parse_args()
    
    # 确定代码模块路径
    if args.code_path:
        code_dir = Path(args.code_path).resolve()
    else:
        code_dir = CODE_MODULE_DIR
    
    if not code_dir.exists():
        print(f"错误: 代码目录不存在: {code_dir}")
        print(f"请使用 --code-path 参数指定正确的路径")
        return
    
    print(f"代码目录: {code_dir}")
    
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 初始化翻译器
    cache = TranslationCache()
    translator = None
    
    # 获取API密钥
    api_key = args.api_key
    if not api_key and API_KEY_FILE.exists():
        try:
            with open(API_KEY_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        api_key = line
                        break
            if api_key:
                print("✓ 已从 ds_api.txt 读取API密钥")
        except:
            pass
    
    if api_key:
        translator = DeepSeekTranslator(api_key, cache)
        print("✓ DeepSeek翻译功能已启用")
    else:
        print("ℹ 未配置API密钥，将使用本地翻译")
    
    # 初始化提取器和生成器
    extractor = ChineseExtractor()
    csv_generator = CSVGenerator(translator)
    
    if args.mode == 'all':
        # 扫描所有子文件夹
        print(f"\n扫描模式: all")
        print(f"输出目录: {OUTPUT_DIR}\n")
        
        for item in sorted(code_dir.iterdir()):
            if item.is_dir() and item.name not in extractor.IGNORE_FOLDERS:
                print(f"扫描文件夹: {item.name}")
                strings = extractor.extract_from_directory(item)
                
                if strings:
                    output_path = OUTPUT_DIR / f"{item.name}.csv"
                    csv_generator.generate(strings, output_path, context=item.name)
                else:
                    print(f"  没有找到中文字符串")
    
    elif args.mode == 'single':
        if not args.folder:
            print("错误: single模式需要指定文件夹名")
            print("用法: python extract_chinese.py single Battle")
            return
        
        target_dir = code_dir / args.folder
        if not target_dir.exists():
            print(f"错误: 文件夹不存在: {target_dir}")
            return
        
        print(f"\n扫描模式: single")
        print(f"扫描目录: {target_dir.name}")
        print(f"输出目录: {OUTPUT_DIR}\n")
        
        strings = extractor.extract_from_directory(target_dir)
        output_path = OUTPUT_DIR / f"{target_dir.name}.csv"
        csv_generator.generate(strings, output_path, context=target_dir.name)
    
    # 保存缓存
    cache.save()
    print(f"\n✓ 提取完成！")
    print(f"✓ 翻译缓存已保存")


if __name__ == '__main__':
    main()
