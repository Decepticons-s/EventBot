# EventBot

一个使用大模型收集历史事件信息并保存到Obsidian知识库的Python工具。

## 功能特点

- 通过交互式命令行界面输入历史事件名称和时间范围
- 调用硅基流动r1大模型生成高质量的历史事件内容
- 将生成的内容自动保存为Markdown格式到Obsidian知识库
- 智能分块请求，避免一次生成过多内容
- 自动限制API调用频率和总token使用量

## 安装

1. 克隆此仓库
2. 安装依赖:

```bash
pip install -r requirements.txt
```

3. 创建`.env`文件，参考`.env.example`设置你的API密钥和Obsidian仓库路径

4. 配置说明

你可以通过修改`config.py`文件或设置环境变量来配置:

- API密钥和端点
- Obsidian仓库路径
- 模型参数
- 内容生成限制

## 使用方法

1. 运行脚本:

```bash
python event_bot.py
```

2. 按照提示输入:
   - 历史事件名称
   - 时间范围
   - 内容分块数量（可选）

3. 等待内容生成完成，结果将自动保存到Obsidian仓库中

4. 运行`python detail_generator.py`生成详细信息

## 注意事项

- 请确保你有有效大模型API访问权限
- 合理设置token数量限制，避免过度使用API
- 生成的内容仅供参考，请自行验证历史信息的准确性