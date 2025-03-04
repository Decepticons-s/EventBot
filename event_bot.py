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
        
    def _check_config(self):
        """检查配置是否正确"""
        if not self.api_key:
            logger.error("未设置API密钥，请在config.py或环境变量中设置R1_API_KEY")
            sys.exit(1)
            
        if not self.obsidian_path:
            logger.warning("未设置Obsidian仓库路径，将使用当前目录下的'obsidian'文件夹")
            self.obsidian_path = os.path.join(os.getcwd(), "obsidian")
            
        # 确保Obsidian仓库目录及事件目录存在
        self.event_dir = os.path.join(self.obsidian_path, self.event_folder)
        os.makedirs(self.event_dir, exist_ok=True)
        logger.info(f"事件将保存到: {self.event_dir}")
    
    def call_model(self, prompt, max_tokens=None, system_prompt=None):
        """调用大模型API
        
        Args:
            prompt: 提示词
            max_tokens: 最大生成token数
            system_prompt: 系统提示词，可选
            
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
            "temperature": 0.7
        }
        
        # 重试机制
        for attempt in range(config.RETRY_ATTEMPTS):
            try:
                logger.info(f"正在调用模型 (第{attempt+1}次尝试)...")
                response = requests.post(
                    self.api_endpoint,
                    headers=headers,
                    json=data,
                    timeout=config.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                self.call_count += 1
                
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                tokens_used = result.get("usage", {}).get("total_tokens", 0)
                self.total_tokens += tokens_used
                
                logger.info(f"调用成功，使用了 {tokens_used} tokens")
                return content
                
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
    
    def get_event_info(self, event_name, time_range, num_parts=3):
        """获取事件信息，分多次调用模型以避免一次生成过多内容
        
        Args:
            event_name: 事件名称
            time_range: 时间范围描述
            num_parts: 将事件分成几部分获取
            
        Returns:
            list: 包含多个部分内容的列表
        """
        if self.total_tokens >= config.MAX_TOKENS_TOTAL:
            logger.warning(f"已达到总token限制 ({config.MAX_TOKENS_TOTAL})，停止生成")
            return ["已达到总token限制，停止生成更多内容。"]
            
        results = []
        system_prompt = "你是一个专业的历史学者，能够提供客观、准确、详细的历史事件信息。请简明扼要地回答问题，不要添加无关的评论。"
        
        for i in range(num_parts):
            part_desc = ""
            if num_parts > 1:
                if i == 0:
                    part_desc = "起因和背景"
                elif i == num_parts - 1:
                    part_desc = "结果和影响"
                else:
                    part_desc = f"发展过程 (第{i}部分)"
                    
            prompt = f"""请详细描述以下历史事件的{part_desc}：
事件名称：{event_name}
时间范围：{time_range}

请只提供客观、准确的历史信息，包括重要日期、人物和事件经过。
内容应该条理清晰，重点突出。不需要额外的评论或解释。
"""

            logger.info(f"正在生成 '{event_name}' 的第 {i+1}/{num_parts} 部分内容...")
            content = self.call_model(prompt, system_prompt=system_prompt)
            results.append(content)
            
            # 在多次请求之间暂停一下，避免频繁调用API
            if i < num_parts - 1:
                time.sleep(1)
                
        return results
    
    def save_to_obsidian(self, event_name, time_range, contents):
        """将生成的内容保存到Obsidian
        
        Args:
            event_name: 事件名称
            time_range: 时间范围
            contents: 生成的内容列表
            
        Returns:
            str: 保存的文件路径
        """
        # 格式化文件名，去除可能导致文件名无效的字符
        safe_event_name = "".join(c for c in event_name if c.isalnum() or c in " _-")
        safe_event_name = safe_event_name.strip().replace(" ", "_")
        
        # 创建文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{safe_event_name}_{timestamp}.md"
        filepath = os.path.join(self.event_dir, filename)
        
        # 准备内容
        full_content = f"""---
event: {event_name}
time_range: {time_range}
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
tags: [event, history]
---

# {event_name}

> 时间范围: {time_range}

"""
        
        # 添加内容
        for i, content in enumerate(contents):
            if len(contents) > 1:
                if i == 0:
                    full_content += "## 起因和背景\n\n"
                elif i == len(contents) - 1:
                    full_content += "## 结果和影响\n\n"
                else:
                    full_content += f"## 发展过程 (第{i}部分)\n\n"
            
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
                
            time_range = input("时间范围（例如：1939-1945）: ").strip()
            
            try:
                parts = int(input("将内容分成几部分获取（默认3）: ").strip() or "3")
            except ValueError:
                parts = 3
            
            print(f"\n正在收集关于 '{event_name}' ({time_range}) 的信息...")
            print("这可能需要一些时间，请耐心等待...\n")
            
            try:
                with tqdm(total=parts, desc="进度") as pbar:
                    contents = []
                    system_prompt = "你是一个专业的历史学者，能够提供客观、准确、详细的历史事件信息。请简明扼要地回答问题，不要添加无关的评论。"
                    
                    for i in range(parts):
                        part_desc = "起因" if i == 0 else ("影响" if i == parts-1 else f"过程{i}")
                        pbar.set_description(f"获取{part_desc}")
                        
                        # 为简化起见，这里直接使用get_event_info方法的部分功能
                        prompt = f"""请详细描述以下历史事件的{'起因和背景' if i == 0 else ('结果和影响' if i == parts-1 else f'发展过程 (第{i}部分)')}：
事件名称：{event_name}
时间范围：{time_range}

请只提供客观、准确的历史信息，包括重要日期、人物和事件经过。
内容应该条理清晰，重点突出。不需要额外的评论或解释。
"""
                        content = self.call_model(prompt, system_prompt=system_prompt)
                        contents.append(content)
                        pbar.update(1)
                        
                        # 避免频繁调用API
                        if i < parts - 1:
                            time.sleep(1)
                
                filepath = self.save_to_obsidian(event_name, time_range, contents)
                
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
