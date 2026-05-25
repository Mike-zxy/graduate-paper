
# LATTE (LLM-Assisted Taint Tracking Engine)

> 基于大语言模型（LLM）与传统程序分析相结合的二进制污点分析引擎。

## 📖 项目简介
LATTE 是一个用于二进制漏洞检测的自动化分析引擎。它创新性地结合了 Ghidra 的反编译能力与 GPT 等大语言模型的语义理解能力，能够更精准地识别二进制程序中的潜在漏洞（如 CWE-78 操作系统命令注入等）。

LATTE 的核心工作流包含：前置函数信息提取 -> LLM 智能识别 Source/Sink -> 危险数据流跟踪与提取 -> LLM 多轮对话漏洞确认。

## ⚙️ 环境依赖
* **反编译引擎**: [Ghidra](https://ghidra-sre.org/) (LATTE 核心脚本 `latte.py` 作为 Ghidra 插件运行)
* **Python**: Python 3.8+ 
* **LLM 接口**: OpenAI API (或兼容的代理接口，如 DeepSeek 等)
* **关键 Python 库**: 
  ```bash
  pip install openai requests httpx python-dotenv

```

## 🚀 核心工作流程与使用指南

LATTE 的分析流程分为以下四个阶段：

### 1. 二进制特征提取 (Ghidra 插件端)

使用 `latte.py` 作为 Ghidra 的插件运行。

* **操作须知**: 在 Ghidra 加载目标程序时，请务必勾选 **"Decompiler Parameter ID"** 选项。
* **功能**: 提取反编译后的函数调用图、变量定义等上下文信息，为后续的污点分析提取函数名。
* **默认输出目录**: `/home/user/Document/LATTE Output/`

### 2. 智能 Source & Sink 识别 (LLM 端)

运行 `ask_source_dest.py` 脚本。

* **功能**: 将第一步提取的候选函数列表喂给大语言模型（如 GPT/DeepSeek），让 LLM 根据语义自动研判并输出可能作为污染源 (Taint Source) 和 危险汇聚点 (Taint Sink) 的目标。
* **命令**:
```bash
python3 ask_source_dest.py

```



### 3. 危险数据流提取 (Ghidra 插件端)

将第二步 LLM 识别出的 Source 和 Sink 结果，结合构造的先验知识库，通过prior.py自动填充至 `config.yaml` 配置文件中。

* **功能**: LATTE (Ghidra 侧) 会根据 `config.yaml` 中的规则，在二进制代码中执行底层的污点跟踪，提取出从 Source 到 Sink 的完整危险数据流 (Dangerous Flows)。

### 4. 漏洞自动化确认 (LLM 端)

运行 `vulchat.py` 脚本。

* **功能**: 针对第三步提取出的危险数据流上下文，与大语言模型进行多轮对话。LLM 会结合数据流的传播路径、过滤机制等，最终判定该数据流是否构成真实的漏洞（如输出 "Vulnerable" 或 "Safe"）。
* **命令**:
```bash
python3 vulchat.py

```



---

## 🛠️ 其他辅助工具集

* **`latte_bench.py`**: 批量自动化测试脚本。用于在多个二进制文件或测试集上自动串联运行 LATTE 的完整流程。
* **`analysis_gptout.py`**: 结果分析与评估脚本。用于解析 LLM 输出的 JSON/文本结果，自动统计真阳性 (TP)、假阳性 (FP) 等混淆矩阵指标，计算模型检测的准确率。

## 📁 目录结构说明

```text
LATTE/
├── data/                  # 存放用于测试的二进制测试用例 (Test cases)
├── prompts/               # 存放与 LLM 交互的 Prompt 模板 (如 vulchat_prompt_v2.json)
├── latte.py               # Ghidra 核心分析插件脚本
├── ask_source_dest.py     # 自动化请求 LLM 识别 Source 和 Sink
├── vulchat.py             # 核心漏洞研判与对话脚本
├── latte_bench.py         # 批量测试运行脚本
├── analysis_gptout.py     # 测评结果统计与分析工具
├── config.yaml            # 污点分析规则配置文件 (需根据分析结果动态填入)
└── Utils.py / utils.py    # 通用文件读写与工具函数

```

## 📝 注意事项

* 默认输出路径写死在代码中 (`/home/user/Document/LATTE Output/`)，在不同设备上运行前请根据实际环境修改相关脚本中的路径变量。
* 调用 LLM API 时请注意配置正确的 `api_key` 和 `base_url`。
* 本文件夹由于ghidra过大没有进行上传，读者需自行安装，且需自动勾选de ID选项作为插件运行
* latte.py,latte_bench.py为python2.7环境下运行
```

```
