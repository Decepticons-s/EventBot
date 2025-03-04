import os
from dotenv import load_dotenv

# 加载环境变量（如果有.env文件）
load_dotenv()

# API相关配置
API_KEY = os.getenv("R1_API_KEY", "")  # 从环境变量获取API密钥
API_ENDPOINT = os.getenv("R1_API_ENDPOINT", "https://api.siliconflow.cn/v1/chat/completions")  # 硅基流动官方API端点

# Obsidian仓库配置
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "")  # Obsidian仓库路径
EVENT_FOLDER = os.getenv("EVENT_FOLDER", "Events")  # 事件文件夹名称

# 模型配置
MODEL_NAME = "deepseek-ai/DeepSeek-R1"  # 官方模型名称
MAX_TOKENS_PER_REQUEST = 1000  # 单次请求最大token数量
MAX_TOKENS_TOTAL = 5000  # 总共允许生成的最大token数量

# 请求配置
REQUEST_TIMEOUT = 60  # 请求超时时间（秒）
RETRY_ATTEMPTS = 3  # 重试次数

# 日志配置
LOG_FILE = "event_bot.log"
