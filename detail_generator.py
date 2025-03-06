"""
MIT License

Copyright (c) 2025 Jason Sun

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

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
        self.detail_folder = "AIdetails"  # 详情文件夹名称
        
        # 检查配置
        self._check_config()
        
        # 初始化路径
        self.event_dir = os.path.join(self.obsidian_path, self.event_folder)
        self.detail_dir = os.path.join(self.obsidian_path, self.detail_folder)
        
        # 确保目录存在
        os.makedirs(self.event_dir, exist_ok=True)
        os.makedirs(self.detail_dir, exist_ok=True)
        
        # 打印实际使用的路径
        logger.info(f"事件列表目录: {self.event_dir}")
        logger.info(f"详情保存目录: {self.detail_dir}")
        
    def _check_config(self):
        """检查配置是否正确"""
        if not self.obsidian_path:
            logger.warning("未设置Obsidian仓库路径，将使用当前目录下的'obsidian_example'文件夹")
            self.obsidian_path = os.path.join(os.getcwd(), "obsidian_example")
            
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
            list: 事件列表，每个事件为字典，包含事件名称和位置信息
        """
        events = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 使用正则表达式提取事件
            # 匹配格式如: {事件名称（xxxx年）}
            pattern = r'{([^{}]+)}'
            matches = re.finditer(pattern, content)
            
            for match in matches:
                event_text = match.group(1).strip()
                if not event_text:
                    continue
                
                events.append({
                    'name': event_text,
                    'original_file': file_path,
                    'original_line_text': match.group(0),
                    'start_position': match.start(),
                    'end_position': match.end()
                })
        except Exception as e:
            logger.error(f"从文件 {file_path} 提取事件时出错: {str(e)}")
        
        return events
    
    def generate_detail_for_event(self, event):
        """为事件生成详细信息
        
        Args:
            event: 事件字典，包含事件名称和位置信息
            
        Returns:
            str: 生成的详细信息，格式为JSON
        """
        event_name = event['name']
        
        # 从事件名称提取年份（如果有）
        year_match = re.search(r'（(\d{4})年）', event_name)
        if year_match:
            happened_year = year_match.group(1)
            # 移除年份部分，获取纯事件名称
            pure_event_name = re.sub(r'（\d{4}年）', '', event_name).strip()
        else:
            happened_year = "未知"
            pure_event_name = event_name
        
        # 创建提示词
        system_prompt = """你是一位专业的历史学者，精通世界历史和中国历史。你的任务是提供客观、准确、详细的历史事件信息。
请以JSON格式输出事件的详细信息，严格按照以下格式：

```json
{
    "title": "事件标题",
    "happened": "发生时间（尽可能精确到年月日）",
    "person": "相关人物（多个人物用逗号分隔）",
    "places": "发生地点（尽可能详细）",
    "tags": "相关标签（多个标签用逗号分隔）",
    "detailes": "详细情况（包括事件背景、经过和影响）"
}
```

请确保：
1. 严格遵循上述JSON格式，保持键名不变
2. 内容客观、准确，避免主观评论
3. 尽可能提供丰富、细致的信息
4. 确保输出的JSON格式正确，可以被解析"""
        
        prompt = f"""请提供以下历史事件的详细信息：
事件名称：{pure_event_name}
发生年份：{happened_year}

请按照系统提示中的JSON格式输出，确保包含事件的发生时间、相关人物、地点、标签和详细情况。
JSON格式必须严格正确，键名不可改变。"""
        
        logger.info(f"正在生成 '{event_name}' 的详细信息...")
        try:
            content = self.event_bot.call_model(prompt, system_prompt=system_prompt, max_tokens=config.MAX_TOKENS_PER_REQUEST)
            
            # 提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                # 如果没有找到```json包裹的内容，尝试直接解析整个内容
                json_content = content
                
            # 尝试解析和格式化JSON
            try:
                detail_data = json.loads(json_content)
                # 格式化为漂亮的JSON字符串
                formatted_json = json.dumps(detail_data, ensure_ascii=False, indent=4)
                return formatted_json
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {str(e)}")
                return content  # 返回原始内容
                
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
        
        # 尝试解析JSON内容
        try:
            detail_data = json.loads(content)
            title = detail_data.get("title", event_name)
            happened = detail_data.get("happened", "未知")
            people = detail_data.get("人物", "未知")
            location = detail_data.get("地点", "未知")
            tags = detail_data.get("tags", "历史,事件")
            details = detail_data.get("detailes", "无详细信息")
            
            # 准备标签列表
            tag_list = ["event", "history", "detail"]
            for tag in tags.split(","):
                tag = tag.strip()
                if tag and tag not in tag_list:
                    tag_list.append(tag)
            
            # 准备元数据和内容
            full_content = f"""---
title: {title}
event: {event_name}
happened: {happened}
people: {people}
location: {location}
tags: {", ".join(tag_list)}
---

# {title}

> 本文是对事件 [[{original_file_rel}|{event_name}]] 的详细介绍

## 基本信息

- **发生时间**：{happened}
- **相关人物**：{people}
- **发生地点**：{location}

## 详细情况

{details}

## 相关链接

- [[{original_file_rel}|返回事件列表]]

"""
        except json.JSONDecodeError:
            # 如果解析JSON失败，使用原始内容
            logger.warning(f"无法解析JSON内容，使用原始格式")
            
            # 准备元数据和内容
            full_content = f"""---
event: {event_name}
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
            
            # 获取原始行文本和位置
            original_line = event['original_line_text']
            start_pos = event['start_position']
            end_pos = event['end_position']
            event_name = event['name']
            
            # 构建新行，保持原始事件格式并添加详情链接
            # 在事件后添加链接，格式为 {事件名称（xxxx年）} [[详情链接|详情]]
            new_line = f"{original_line} [[{detail_link}|详情]]"
            
            # 替换内容，精确定位到原始行的位置
            new_content = content[:start_pos] + new_line + content[end_pos:]
            
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
            
            if not detail_content or "错误" in detail_content:
                logger.error(f"生成事件 '{event_name}' 的详细信息失败")
                continue
                
            # 保存详细信息
            filepath, rel_detail_path = self.save_detail_to_obsidian(event, detail_content)
            
            if filepath:
                # 更新事件列表，添加详情链接
                updated = self.update_event_list_with_link(event, rel_detail_path)
                if updated:
                    successful_details += 1
                    print(f"✅ 已成功生成并保存事件 '{event_name}' 的详细信息")
                else:
                    print(f"⚠️ 已保存事件 '{event_name}' 的详细信息，但未能更新链接")
            else:
                print(f"❌ 保存事件 '{event_name}' 的详细信息失败")
            
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
