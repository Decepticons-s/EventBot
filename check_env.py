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
