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
事件收集机器人 - 调用硅基流动r1大模型生成指定事件的内容并保存到Obsidian
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from tqdm import tqdm
import config
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("EventBot")

class EventBot:
    """事件收集机器人，用于调用大模型生成事件内容并保存到Obsidian"""
    
    def __init__(self):
        """初始化事件机器人"""
        self.api_key = config.API_KEY
        self.api_endpoint = config.API_ENDPOINT
        self.model_name = config.MODEL_NAME
        self.obsidian_path = config.OBSIDIAN_VAULT_PATH
        self.event_folder = config.EVENT_FOLDER
        self.call_count = 0
        self.total_tokens = 0
        
        # 检查配置
        self._check_config()
        
        # 初始化路径
        self.event_dir = os.path.join(self.obsidian_path, self.event_folder)
        os.makedirs(self.event_dir, exist_ok=True)
        
        # 添加日志输出，打印实际路径
        logger.info(f"事件将保存到: {self.event_dir}")
        
    def _check_config(self):
        """检查配置是否正确"""
        if not self.api_key:
            logger.warning("未设置API密钥，某些功能可能无法正常使用")
            
        # 如果未设置Obsidian仓库路径，则使用当前目录
        if not self.obsidian_path:
            logger.warning("未设置Obsidian仓库路径，将使用当前目录下的'obsidian'文件夹")
            self.obsidian_path = os.path.join(os.getcwd(), "obsidian")
            
    def call_model(self, prompt, max_tokens=None, system_prompt=None, stream=True):
        """调用大模型API
        
        Args:
            prompt: 提示词
            max_tokens: 最大生成token数
            system_prompt: 系统提示词，可选
            stream: 是否使用流式输出，默认为True
            
        Returns:
            str: 模型返回的内容
        """
        if not max_tokens:
            max_tokens = config.MAX_TOKENS_PER_REQUEST
            
        if not system_prompt:
            system_prompt = "你是一个专业的历史学者，能够提供客观、准确、详细的历史事件信息。请简明扼要地回答问题，不要添加无关的评论。"
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 按照官方API格式构建请求
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        data = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.4,
            "stream": stream  # 开启流式响应
        }
        
        full_content = ""
        tokens_used = 0
        
        # 重试机制
        for attempt in range(config.RETRY_ATTEMPTS):
            try:
                logger.info(f"正在调用模型 (第{attempt+1}次尝试)...")
                
                if stream:
                    # 流式处理
                    response = requests.post(
                        self.api_endpoint,
                        headers=headers,
                        json=data,
                        timeout=config.REQUEST_TIMEOUT,
                        stream=True  # 启用流式传输
                    )
                    response.raise_for_status()
                    self.call_count += 1
                    
                    # 处理流式响应
                    print("\n模型正在思考...\n")
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith("data: "):
                                if line == "data: [DONE]":
                                    break
                                    
                                # 解析JSON数据
                                try:
                                    json_data = json.loads(line[6:])  # 去掉"data: "前缀
                                    delta_content = json_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if delta_content:
                                        print(delta_content, end="", flush=True)
                                        full_content += delta_content
                                except json.JSONDecodeError:
                                    pass
                    
                    print("\n")  # 打印一个换行，表示响应结束
                    
                    # 尝试获取token使用信息（流式模式下可能没有）
                    tokens_used = 0  # 流式模式下可能无法获取准确的token数
                    
                else:
                    # 非流式处理
                    response = requests.post(
                        self.api_endpoint,
                        headers=headers,
                        json=data,
                        timeout=config.REQUEST_TIMEOUT
                    )
                    response.raise_for_status()
                    self.call_count += 1
                    
                    result = response.json()
                    full_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    tokens_used = result.get("usage", {}).get("total_tokens", 0)
                
                self.total_tokens += tokens_used
                logger.info(f"调用成功，使用了约 {tokens_used} tokens")
                return full_content
                
            except requests.exceptions.RequestException as e:
                logger.error(f"API调用失败: {str(e)}")
                if attempt < config.RETRY_ATTEMPTS - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error("达到最大重试次数，放弃请求")
                    return "抱歉，无法连接到模型服务。请检查网络连接或API配置。"
        
        return "发生未知错误"
    
    def parse_time_range(self, time_range):
        """解析时间范围
        
        Args:
            time_range: 时间范围字符串，格式如 "2000-2024"
            
        Returns:
            tuple: (开始年份, 结束年份)
        """
        # 使用正则表达式提取年份
        match = re.match(r'(\d{1,4})-(\d{1,4})', time_range)
        if match:
            start_year = int(match.group(1))
            end_year = int(match.group(2))
            return start_year, end_year
        else:
            # 如果格式不匹配，返回原始字符串作为整体时间范围
            logger.warning(f"无法解析时间范围: {time_range}，将作为整体处理")
            return time_range, time_range
    
    def split_time_range(self, start_year, end_year, segments):
        """将时间范围分割成多个段
        
        Args:
            start_year: 开始年份
            end_year: 结束年份
            segments: 分段数量
            
        Returns:
            list: 包含多个时间段的列表，每个元素为 (段开始年份, 段结束年份)
        """
        total_years = end_year - start_year + 1
        # 计算每段的年数（向上取整）
        years_per_segment = (total_years + segments - 1) // segments
        
        time_segments = []
        current_year = start_year
        
        for i in range(segments):
            segment_start = current_year
            segment_end = min(current_year + years_per_segment - 1, end_year)
            time_segments.append((segment_start, segment_end))
            
            current_year = segment_end + 1
            if current_year > end_year:
                break
                
        return time_segments
    
    def get_event_for_time_segment(self, event_name, start_year, end_year):
        """获取特定时间段内的事件信息
        
        Args:
            event_name: 事件名称
            start_year: 开始年份
            end_year: 结束年份
            
        Returns:
            str: 获取到的事件内容
        """
        if self.total_tokens >= config.MAX_TOKENS_TOTAL:
            logger.warning(f"已达到总token限制 ({config.MAX_TOKENS_TOTAL})，停止生成")
            return "已达到总token限制，停止生成更多内容。"
            
        time_range = f"{start_year}-{end_year}"
        system_prompt = """你是一个专业的历史学者，能够提供客观、准确、详细的历史事件信息。
请列出指定时间范围内的重要历史事件，每行一个事件，格式必须严格按照：
{事件名称（xxxx年）}

例如：
{甲午战争爆发（1894年）}
{《马关条约》签订（1895年）}

注意：
1. 严格遵循 {事件名称（xxxx年）} 的格式，不要添加其他内容
2. 确保所有事件都在指定的时间范围内
3. 只列出重要且有明确年份的事件
4. 事件要足够细致，不要遗漏重要事件
5. 不要添加编号、序号或其他前缀
6. 不要加入未经确认的事件或模糊的时间点"""
        
        prompt = f"""请列出在{time_range}年间与"{event_name}"相关的所有重要历史事件。
每个事件必须包含明确的年份，并且严格按照 {{事件名称（xxxx年）}} 的格式呈现。
不要添加任何编号、解释或其他内容。"""
        
        logger.info(f"正在生成 '{event_name}' 在 {time_range} 年间的内容...")
        content = self.call_model(prompt, system_prompt=system_prompt)
        return content
    
    def save_event_to_obsidian(self, event_name, start_year, end_year, content):
        """将事件内容保存到Obsidian
        
        Args:
            event_name: 事件名称
            start_year: 开始年份
            end_year: 结束年份
            content: 事件内容
            
        Returns:
            str: 保存的文件路径
        """
        # 格式化文件名，去除可能导致文件名无效的字符
        safe_event_name = "".join(c for c in event_name if c.isalnum() or c in " _-")
        safe_event_name = safe_event_name.strip().replace(" ", "_")
        
        # 创建文件名，不包含时间戳
        time_range = f"{start_year}-{end_year}"
        filename = f"{safe_event_name}_{time_range}.md"
        filepath = os.path.join(self.event_dir, filename)
        
        # 检查文件是否已存在，如果存在则加上序号
        if os.path.exists(filepath):
            count = 1
            while os.path.exists(filepath):
                filename = f"{safe_event_name}_{time_range}_{count}.md"
                filepath = os.path.join(self.event_dir, filename)
                count += 1
            logger.info(f"文件已存在，将使用新文件名: {filename}")
        
        # 准备内容
        full_content = f"""---
event: {event_name}
time_range: {time_range}
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
tags: [event, history]
---

# {event_name} ({time_range})

"""
        
        # 添加内容
        full_content += content + "\n\n"
        
        # 保存文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)
            
        logger.info(f"已保存到: {filepath}")
        return filepath
        
    def interactive_session(self):
        """启动交互式会话"""
        print("\n===============================")
        print("  历史事件收集机器人")
        print("  基于硅基流动r1大模型")
        print("===============================\n")
        
        while True:
            print("\n请输入要收集的历史事件信息（输入'退出'结束程序）:")
            event_name = input("事件名称: ").strip()
            
            if event_name.lower() in ['退出', 'exit', 'quit', 'q']:
                print("感谢使用，再见！")
                break
                
            time_range = input("时间范围（例如：2000-2024）: ").strip()
            
            try:
                segments = int(input("将内容分成几部分获取（默认3）: ").strip() or "3")
            except ValueError:
                segments = 3
            
            # 解析时间范围
            try:
                start_year, end_year = self.parse_time_range(time_range)
                
                # 如果开始年份和结束年份相同，就不再划分时间段
                if isinstance(start_year, int) and isinstance(end_year, int) and start_year != end_year:
                    # 将时间范围分割成多个段
                    time_segments = self.split_time_range(start_year, end_year, segments)
                    total_segments = len(time_segments)
                    
                    print(f"\n已将时间范围 {start_year}-{end_year} 分为 {total_segments} 个时间段:")
                    for i, (seg_start, seg_end) in enumerate(time_segments):
                        print(f"  时间段 {i+1}: {seg_start}-{seg_end}")
                        
                    print(f"\n开始收集关于 '{event_name}' 的信息...")
                    print("每个时间段的内容将立即保存到Obsidian仓库中...\n")
                    
                    # 使用tqdm显示总体进度
                    with tqdm(total=total_segments, desc="总进度") as pbar:
                        saved_files = []
                        
                        for i, (seg_start, seg_end) in enumerate(time_segments):
                            seg_desc = f"{seg_start}-{seg_end}"
                            pbar.set_description(f"处理{seg_desc}")
                            
                            # 获取当前时间段的事件内容
                            content = self.get_event_for_time_segment(event_name, seg_start, seg_end)
                            
                            # 立即保存到Obsidian
                            filepath = self.save_event_to_obsidian(event_name, seg_start, seg_end, content)
                            saved_files.append(filepath)
                            
                            pbar.update(1)
                            
                            # 避免频繁调用API
                            if i < total_segments - 1:
                                time.sleep(1)
                        
                        print(f"\n✅ 已完成所有时间段的内容收集和保存")
                        print(f"API调用次数: {self.call_count}, 总token使用: {self.total_tokens}")
                        print(f"已保存 {len(saved_files)} 个文件到Obsidian仓库")
                else:
                    # 如果时间范围无法解析或者是单一年份，则作为整体处理
                    print(f"\n正在收集关于 '{event_name}' ({time_range}) 的信息...")
                    content = self.get_event_for_time_segment(event_name, start_year, end_year)
                    filepath = self.save_event_to_obsidian(event_name, start_year, end_year, content)
                    
                    print(f"\n✅ 内容已保存到: {filepath}")
                    print(f"API调用次数: {self.call_count}, 总token使用: {self.total_tokens}")
            
            except KeyboardInterrupt:
                print("\n操作已取消")
            except Exception as e:
                logger.error(f"处理 '{event_name}' 时出错: {str(e)}")
                print(f"\n⚠️ 发生错误: {str(e)}")
        
def main():
    """主函数"""
    try:
        bot = EventBot()
        bot.interactive_session()
    except KeyboardInterrupt:
        print("\n程序已终止")
    except Exception as e:
        logger.error(f"程序异常: {str(e)}")
        print(f"\n⚠️ 程序异常: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
