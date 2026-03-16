## 项目概览

本仓库包含一些小工具，用于基于**真实课堂材料**学习中文：

- **音频转写流水线**：把课堂录音转换为经过清理、带时间戳的文字稿。
- **口语 / 精读词汇工具**：读取教材或课堂文字稿，生成结构化的词汇表。
- **课堂总结工具**（计划中）：根据最终文字稿生成结构化的课堂总结和作业说明。

代码最初是为一门具体课程而写，但设计目标是：**任何有自己原始学习材料的学习者都可以复用**。

## 目录结构

- `raw_materials/`（被 git 忽略）
  - `audio_lectures/`：课堂原始录音文件（例如 `.m4a`、`.wav`）。
  - `textbooks/`：教材 PDF 与其他参考文档。
  - `first_pass_transcripts/`：粗略或中间版本的转写文本（应保持私密）。
- `apps/`
  - `transcriber/`：离线转写代码（例如基于 faster-whisper 或其他后端）。
  - `textbook_vocab/`：从教材或文字稿中构建词汇表的工具。
  - `class_summarizer/`：对最终课堂文字稿进行 LLM 总结（尚未实现）。
- `outputs/`：生成的结果，例如清理后的文字稿、词汇 CSV、总结草稿等。
- `old_materials/`：旧脚本和笔记，仅作参考保留。
- `scripts/`：运行常用工作流的小型 shell 脚本（例如转写、抽取词汇）。

## 隐私与原始材料

所有原始媒体与个人学习材料**只保存在本地**，不会被提交到 GitHub：

- 课堂录音、教材 PDF 与个人笔记统一放在 `raw_materials/` 目录下。
- 根目录下的 `.gitignore` 已配置忽略整个 `raw_materials/` 树。
- 当其他人克隆或派生本项目时，他们需要在本地按照相同目录结构放入自己的学习材料。

## 本地使用步骤

1. 创建并激活 Python 虚拟环境，例如：
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
2. 安装 Python 依赖：
   - `pip install -r requirements.txt`
3. 如不存在，则创建 `raw_materials/` 目录结构：
   - `raw_materials/audio_lectures/`
   - `raw_materials/textbooks/`
   - `raw_materials/first_pass_transcripts/`
4. 将自己的课堂录音、教材与粗略转写文件放入对应子目录。
5. 通过 `scripts/` 中的便捷脚本（例如 `run_transcription.sh`），或直接运行 `apps/` 下的各个子应用，按照各自的 README 或帮助说明执行。

