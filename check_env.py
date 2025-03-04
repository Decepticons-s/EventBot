import os
from dotenv import load_dotenv
import config  # 导入config模块，这会触发环境变量的设置

# 加载环境变量
load_dotenv()

# 打印环境变量值
print(f"EVENT_FOLDER环境变量: {os.getenv('EVENT_FOLDER', '<未设置>')}")
print(f"EVENT_FOLDER从config: {config.EVENT_FOLDER}")
print(f"OBSIDIAN_VAULT_PATH环境变量: {os.getenv('OBSIDIAN_VAULT_PATH', '<未设置>')}")
print(f"R1_API_KEY环境变量前几位: {os.getenv('R1_API_KEY', '<未设置>')[:5] if os.getenv('R1_API_KEY') else '<未设置>'}")
