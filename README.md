# NOTION 外挂AI智能体
这是一个集成了大型语言模型（LLM）的 Notion 智能体，能够根据用户的指令自动在 Notion 中创建和更新内容。智能体通过调用 Notion API 与 Notion 进行交互，并利用 LLM 生成高质量的文本内容。
## 功能特点
能够根据用户的自然语言指令，在 Notion 页面中创建和更新内容。支持各种模型，写好了多种工具函数，方便扩展。预设了通用的智能体思维流程，能够高效地处理复杂任务。
## 安装与配置
1. 克隆代码库：
```bash
git clone
```
2. 安装依赖：
```bash
uv sync
```
3. 配置环境变量：
创建 `.env` 文件，参考 `.env.example`，填写 Notion API 密钥和 LLM 配置。
```bash
cp .env.example .env
```
创建 `notion_config.json` 文件，参考 `notion_config.json.example`，填写 Notion 相关配置。
```bash
cp notion_config.json.example notion_config.json
```
4. 运行智能体：
```bash
uv run agent.py
```

**仍处于开发阶段**
目前没有写成接口形式，是因为想先把核心功能打磨好，后续会考虑做成API形式，方便直接在notion直接调用，这是完全可以做到的。
notion的配置没有写在.env里，是因为未来考虑支持多个智能体或多个页面，放在json里更清晰。

