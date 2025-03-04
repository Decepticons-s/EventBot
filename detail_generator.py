#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
详情生成器 - 遍历Obsidian仓库中的事件列表文件，为每个事件生成详细信息
并保存到detail文件夹中，同时使用Obsidian的双链语法建立双向链接
"""

import os
import sys
import re
import json
import time
import logging
from datetime import datetime
from pathlib import Path
import config
from event_bot import EventBot

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DetailGenerator")

class DetailGenerator:
    """详情生成器，遍历Obsidian仓库中的事件列表，生成详细信息并保存"""
    
    def __init__(self):
        """初始化详情生成器"""
        self.event_bot = EventBot()  # 实例化事件机器人用于调用模型
        self.obsidian_path = config.OBSIDIAN_VAULT_PATH
        self.event_folder = config.EVENT_FOLDER
        self.detail_folder = "Details"  # 详情文件夹名称
        
        # 检查配置
        self._check_config()
        
    def _check_config(self):
        """检查配置是否正确"""
        if not self.obsidian_path:
            logger.warning("未设置Obsidian仓库路径，将使用当前目录下的'obsidian'文件夹")
            self.obsidian_path = os.path.join(os.getcwd(), "obsidian")
            
        # 检查Obsidian仓库路径是否存在
        if not os.path.exists(self.obsidian_path):
            logger.warning(f"Obsidian仓库路径 {self.obsidian_path} 不存在，将在当前目录下创建示例目录结构")
            # 使用当前目录
            self.obsidian_path = os.path.join(os.getcwd(), "obsidian_example")
            
        # 确保Obsidian仓库目录、事件目录和详情目录存在
        self.event_dir = os.path.join(self.obsidian_path, self.event_folder)
        self.detail_dir = os.path.join(self.obsidian_path, self.detail_folder)
        
        os.makedirs(self.event_dir, exist_ok=True)
        os.makedirs(self.detail_dir, exist_ok=True)
        
        logger.info(f"事件列表目录: {self.event_dir}")
        logger.info(f"详情保存目录: {self.detail_dir}")
        
        # 如果没有找到任何事件列表文件，创建一个示例文件
        if not os.listdir(self.event_dir):
            example_file = os.path.join(self.event_dir, "example_events.md")
            logger.info(f"未找到事件列表文件，创建示例文件: {example_file}")
            
            example_content = """---
title: 示例历史事件列表
created: 2025-03-04
tags: [history, events, example]
---

# 示例历史事件列表

以下是一些历史事件的示例列表：

- 第二次世界大战 (1939-1945)
- 美国独立战争 (1775-1783)
- 法国大革命 (1789-1799)
- 中国改革开放 (1978-2000)
- 苏联解体 (1991)
"""
            with open(example_file, "w", encoding="utf-8") as f:
                f.write(example_content)
                
    def find_event_list_files(self):
        """查找所有事件列表文件
        
        Returns:
            list: 事件列表文件路径
        """
        event_list_files = []
        
        try:
            # 遍历事件目录，找到所有.md文件
            for root, _, files in os.walk(self.event_dir):
                for file in files:
                    if file.endswith('.md'):
                        event_list_files.append(os.path.join(root, file))
        except Exception as e:
            logger.error(f"查找事件列表文件时出错: {str(e)}")
            
        logger.info(f"找到 {len(event_list_files)} 个事件列表文件")
        return event_list_files
    
    def extract_events_from_file(self, file_path):
        """从事件列表文件中提取事件
        
        Args:
            file_path: 事件列表文件路径
            
        Returns:
            list: 事件列表，每个事件为字典，包含事件名称和时间范围
        """
        events = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 使用正则表达式提取事件
            # 匹配格式如: - 事件名称 (1900-2000)
            # 或者: - 事件名称（1900-2000）
            # 或者只有事件名称的行
            pattern = r'[-*]\s+([^(（\r\n]+)(?:\s*[(（]([^)）]+)[)）])?'
            matches = re.finditer(pattern, content)
            
            for match in matches:
                event_name = match.group(1).strip()
                time_range = match.group(2).strip() if match.group(2) else None
                
                if not event_name:
                    continue
                    
                # 处理时间范围
                if time_range:
                    # 尝试解析时间范围
                    try:
                        # 匹配中文年份或西方年份格式
                        year_match = re.search(r'(\d{1,4})[-~到至](\d{1,4})', time_range)
                        if year_match:
                            start_year = int(year_match.group(1))
                            end_year = int(year_match.group(2))
                        else:
                            # 如果没有明确的时间范围格式，直接使用原始时间范围
                            start_year = time_range
                            end_year = time_range
                    except:
                        start_year = time_range
                        end_year = time_range
                else:
                    # 如果没有提供时间范围，使用通用时间范围
                    start_year = "古代"
                    end_year = "现代"
                
                events.append({
                    'name': event_name,
                    'start_year': start_year,
                    'end_year': end_year,
                    'original_file': file_path,
                    'original_line_text': match.group(0)
                })
        except Exception as e:
            logger.error(f"从文件 {file_path} 提取事件时出错: {str(e)}")
        
        return events
    
    def generate_detail_for_event(self, event):
        """为事件生成详细信息
        
        Args:
            event: 事件字典，包含事件名称和时间范围
            
        Returns:
            str: 生成的详细信息
        """
        event_name = event['name']
        start_year = event['start_year']
        end_year = event['end_year']
        
        if isinstance(start_year, int) and isinstance(end_year, int):
            time_range = f"{start_year}-{end_year}"
        else:
            time_range = f"{start_year}至{end_year}"
        
        # 创建提示词
        system_prompt = """你是一位专业的历史学者，精通世界历史和中国历史。你的任务是提供客观、准确、详细的历史事件信息。
请按照以下确切的格式组织内容，使用二级标题和段落：

## 概述
[简要介绍事件的背景、主要内容和历史意义，100-200字]

## 起因与背景
[详细分析事件发生的原因和历史背景，200-300字]

## 经过与发展
[按时间顺序详细描述事件的发展过程和关键节点，包含具体日期和重要人物，300-500字]

## 结果与影响
[说明事件的直接结果和短期影响，200-300字]

## 历史意义
[分析事件在历史长河中的重要性和长远影响，200-300字]

请确保内容客观、准确，避免主观评论和现代视角的价值判断。严格按照以上格式输出，使用Markdown语法。"""
        
        prompt = f"""请详细介绍以下历史事件：
事件名称：{event_name}
时间范围：{time_range}

请提供详尽的历史背景、事件经过、重要人物及其作用、事件影响和历史意义等内容。
内容应该条理清晰，重点突出，包含准确的时间节点和历史细节。
如果有不同的历史观点或解释，请一并说明。
请确保回答的内容完全符合系统提示中规定的格式要求。"""
        
        logger.info(f"正在生成 '{event_name}' 的详细信息...")
        try:
            content = self.event_bot.call_model(prompt, system_prompt=system_prompt, max_tokens=config.MAX_TOKENS_PER_REQUEST)
            return content
        except Exception as e:
            logger.error(f"生成详细信息时出错: {str(e)}")
            return f"生成详细信息时出错: {str(e)}"
    
    def save_detail_to_obsidian(self, event, content):
        """将详细信息保存到Obsidian
        
        Args:
            event: 事件字典
            content: 生成的详细信息
            
        Returns:
            str: 保存的文件路径
        """
        event_name = event['name']
        
        # 格式化文件名，去除可能导致文件名无效的字符
        safe_event_name = "".join(c for c in event_name if c.isalnum() or c in " _-")
        safe_event_name = safe_event_name.strip().replace(" ", "_")
        
        # 创建文件名，不包含时间戳
        filename = f"{safe_event_name}_详情.md"
        filepath = os.path.join(self.detail_dir, filename)
        
        # 检查文件是否已存在，如果存在则加上序号
        if os.path.exists(filepath):
            count = 1
            while os.path.exists(filepath):
                filename = f"{safe_event_name}_详情_{count}.md"
                filepath = os.path.join(self.detail_dir, filename)
                count += 1
            logger.info(f"文件已存在，将使用新文件名: {filename}")
        
        # 获取相对路径，用于创建双链
        rel_detail_path = os.path.relpath(filepath, self.obsidian_path)
        original_file_rel = os.path.relpath(event['original_file'], self.obsidian_path)
        
        # 准备元数据和内容
        time_range = f"{event['start_year']}-{event['end_year']}" if isinstance(event['start_year'], int) and isinstance(event['end_year'], int) else f"{event['start_year']}至{event['end_year']}"
        full_content = f"""---
event: {event_name}
time_range: {time_range}
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
tags: [event, history, detail]
---

# {event_name} 详细信息

> 本文是对事件 [[{original_file_rel}|{event_name}]] 的详细介绍

{content}

## 相关链接

- [[{original_file_rel}|返回事件列表]]

"""
        
        # 保存文件
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_content)
            logger.info(f"已保存详细信息到: {filepath}")
            return filepath, rel_detail_path
        except Exception as e:
            logger.error(f"保存详细信息时出错: {str(e)}")
            return None, None
    
    def update_event_list_with_link(self, event, detail_link):
        """更新事件列表文件，添加到详情页面的链接
        
        Args:
            event: 事件字典
            detail_link: 详情页面的相对路径
            
        Returns:
            bool: 是否成功更新
        """
        try:
            # 读取原文件内容
            with open(event['original_file'], 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换匹配的行，添加详情链接
            original_line = event['original_line_text']
            event_name = event['name']
            
            # 构建新行，在原行后添加详情链接
            if '[[' in original_line:
                # 如果原行已经包含链接，可能需要更复杂的处理
                new_line = original_line + f" - [[{detail_link}|详情]]"
            else:
                new_line = original_line + f" - [[{detail_link}|详情]]"
            
            # 替换内容
            new_content = content.replace(original_line, new_line)
            
            # 保存更新后的文件
            with open(event['original_file'], 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"已更新事件列表文件，添加详情链接")
            return True
        except Exception as e:
            logger.error(f"更新事件列表文件时出错: {str(e)}")
            return False
    
    def process_event_list_file(self, file_path):
        """处理单个事件列表文件
        
        Args:
            file_path: 事件列表文件路径
            
        Returns:
            tuple: (处理的事件数, 成功生成的详情数)
        """
        logger.info(f"正在处理事件列表文件: {file_path}")
        
        # 提取事件
        events = self.extract_events_from_file(file_path)
        logger.info(f"从文件中提取到 {len(events)} 个事件")
        
        if not events:
            logger.warning(f"文件中未找到任何事件: {file_path}")
            return 0, 0
        
        successful_details = 0
        
        # 处理每个事件
        for i, event in enumerate(events):
            event_name = event['name']
            logger.info(f"处理事件 [{i+1}/{len(events)}]: {event_name}")
            
            # 生成详细信息
            detail_content = self.generate_detail_for_event(event)
            
            # 保存详细信息
            filepath, rel_detail_path = self.save_detail_to_obsidian(event, detail_content)
            
            if filepath:
                # 更新事件列表，添加详情链接
                updated = self.update_event_list_with_link(event, rel_detail_path)
                if updated:
                    successful_details += 1
            
            # 处理完一个事件后稍作停顿，避免频繁调用API
            if i < len(events) - 1:
                time.sleep(1)
        
        return len(events), successful_details
    
    def process_all_event_lists(self):
        """处理所有事件列表文件"""
        # 查找所有事件列表文件
        event_list_files = self.find_event_list_files()
        
        if not event_list_files:
            logger.warning("未找到任何事件列表文件")
            return
        
        total_events = 0
        total_successful = 0
        
        print("\n===============================")
        print("  事件详情生成器")
        print("  基于硅基流动r1大模型")
        print("===============================\n")
        
        print(f"找到 {len(event_list_files)} 个事件列表文件")
        
        # 处理每个文件
        for i, file_path in enumerate(event_list_files):
            print(f"\n处理文件 [{i+1}/{len(event_list_files)}]: {os.path.basename(file_path)}")
            
            events_count, successful_count = self.process_event_list_file(file_path)
            total_events += events_count
            total_successful += successful_count
            
            # 处理完一个文件后稍作停顿
            if i < len(event_list_files) - 1:
                time.sleep(1)
        
        print("\n===============================")
        print(f"处理完成！")
        print(f"共处理 {len(event_list_files)} 个文件")
        print(f"共提取 {total_events} 个事件")
        print(f"成功生成 {total_successful} 个详情页面")
        print(f"API调用次数: {self.event_bot.call_count}")
        print(f"总token使用: {self.event_bot.total_tokens}")
        print("===============================\n")


def main():
    """主函数"""
    try:
        generator = DetailGenerator()
        
        # 查找所有事件列表文件
        event_list_files = generator.find_event_list_files()
        
        if not event_list_files:
            logger.warning("未找到任何事件列表文件")
            print("\n未找到任何事件列表文件。请确保Obsidian仓库路径正确，并且其中包含事件列表文件。")
            print(f"当前事件列表目录: {generator.event_dir}")
            print("已创建示例文件，您可以修改此文件或添加新文件后重新运行程序。")
            return 0
            
        generator.process_all_event_lists()
    except KeyboardInterrupt:
        print("\n程序已终止")
    except Exception as e:
        logger.error(f"程序异常: {str(e)}")
        print(f"\n⚠️ 程序异常: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
