import os
import sys
import time
import random
import json
import signal
import functools
import re
from datetime import datetime
from openai import OpenAI, APIConnectionError, RateLimitError, APIError

# Support both `Utils.py` and `utils.py`.
try:
    from Utils import * # noqa: F401,F403
except ImportError:
    from utils import * # type: ignore # noqa: F401,F403

# === 配置路径变量 ===
# IMPORTANT: `vulchat.py` expects a JSON *prompt list* (array of strings) that includes code + taint context,
# e.g. files like `*.out-0.json` under `Potentially Vulnerable/*`.
# Do NOT point this to `Decompile_result/*function_name.json` (that's just a function-name map).
dir = "/home/user/Document/LATTE_Output/Potentially Vulnerable/CWE_78_bad/"
debug = "/home/user/Document/debug.json"
record = "/home/user/Document/record.json"
file_out = "/home/user/Document/GPT_78_bad/"

Vul_check = {}
base = ["Yes", "highly likely"]
PROMPT_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", "vulchat_prompt_v2.json")

# === 初始化 OpenAI 客户端 ===
client = OpenAI(
    api_key="sk-WyDMwTn9hn98tcFDrJ5iFA",
    base_url="https://xplt.sdu.edu.cn:4000/v1"
)

def aoai_ask(prompt, model="Ali-dashscope/DeepSeek-V3.2", temperature=0.5):
    knowledge_cutoff = "2025-09-01"
    current_date = datetime.now().strftime("%Y-%m-%d")

    if isinstance(prompt, str):
        system_prompt = f"You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible. Knowledge cutoff: {knowledge_cutoff} Current date: {current_date}"
        final_prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    elif isinstance(prompt, list):
        final_prompt = prompt
    else:
        raise TypeError("Expected a string or list as input") 

    try:
        response = client.chat.completions.create(
            model=model,
            messages=final_prompt,
            temperature=temperature,
            max_tokens=2000,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None
        )
    except APIConnectionError:
        print("API Connection Error, retrying...")
        time.sleep(5)
        response = client.chat.completions.create(
            model=model,
            messages=final_prompt,
            temperature=temperature,
            max_tokens=2000,
            top_p=0.95
        )
    except RateLimitError:
        print("The server is currently overloaded. Sleep 1 mins and retry...")
        time.sleep(60)
        response = client.chat.completions.create(
            model=model,
            messages=final_prompt,
            temperature=temperature,
            max_tokens=2000,
            top_p=0.95
        )
    except APIError as e:
        print("Invalid response object from API, retrying...")
        print("APIError detail:", repr(e))
        time.sleep(60)
        response = client.chat.completions.create(
            model=model,
            messages=final_prompt,
            temperature=temperature,
            max_tokens=2000,
            top_p=0.95
        )
        
    text = response.choices[0].message.content
    return text


def _load_prompt_template():
    """
    Load the structured-output prompt template if present.
    Falls back to the legacy concise system prompt if missing.
    """
    try:
        with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _try_parse_json(s: str):
    try:
        # 修复3: 清洗大模型输出的 Markdown 格式，防止 json.loads 解析失败
        # 使用动态字符串生成反引号，防止渲染器截断代码框
        s = s.strip()
        fence = '`' * 3
        if s.startswith(fence):
            s = re.sub(r"^" + fence + r"(?:json)?\s*", "", s, flags=re.IGNORECASE)
        if s.endswith(fence):
            s = re.sub(r"\s*" + fence + r"$", "", s)
        s = s.strip()
        
        return json.loads(s), None
    except Exception as e:
        return None, str(e)


def timeout(sec):
    """
    timeout decorator
    :param sec: function raise TimeoutError after ? seconds
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            def _handle_timeout(signum, frame):
                err_msg = f'Function {func.__name__} timed out after {sec} seconds'
                raise TimeoutError(err_msg)

            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(sec)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result
        return wrapped_func
    return decorator


def random_surround_color(s):
    return random.choice(
        ["\033[1;31m", "\033[1;32m", "\033[1;33m", "\033[1;34m",
         "\033[1;35m", "\033[1;36m", "\033[1;37m", "\033[1;38m"]
    ) + s + "\033[0m"


@timeout(300)
def prompt_conver(file, file_name):
    print(f'\n{random_surround_color("analysis " + file_name)}')
    print(time.strftime("%Y-%m-%d %H:%M:%S"))
    time.sleep(5)
    
    # 获取问题列表
    question_list = load_file(file)
    # Normalize inputs:
    # - expected: JSON array (list[str]) of prompts
    # - some upstream files are double-encoded JSON strings; decode repeatedly
    if isinstance(question_list, str):
        for _ in range(3):
            try:
                decoded = json.loads(question_list)
            except Exception:
                break
            question_list = decoded
            if not isinstance(question_list, str):
                break

    # Guard: if it's not a prompt list, do not iterate character-by-character.
    if not isinstance(question_list, list):
        raise ValueError(
            f"Input file is not a JSON prompt list. Got {type(question_list).__name__} from {file}. "
            "This usually means you're pointing vulchat.py at a function-name map (Decompile_result) "
            "instead of dangerous-flow prompt files (Potentially Vulnerable)."
        )

    prompt_len = len(question_list)
    res = []
    
    # 构建多轮对话初始上下文
    knowledge_cutoff = "2025-09-01"
    current_date = datetime.now().strftime("%Y-%m-%d")
    template = _load_prompt_template()
    if template and isinstance(template, dict) and template.get("system") and template.get("final_user"):
        system_prompt = template["system"]
        final_user_prompt = template["final_user"]
        structured_mode = True
    else:
        system_prompt = f"You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible. Knowledge cutoff: {knowledge_cutoff} Current date: {current_date}"
        final_user_prompt = None
        structured_mode = False

    messages = [{"role": "system", "content": system_prompt}]

    if file_name not in Vul_check:
        Vul_check[file_name] = {}

    # 动态处理任意长度的问题列表
    for i in range(prompt_len):
        prompt = question_list[i]
        
        # 修复2: 拼接格式化指令，而不是直接覆盖用户的原始问题
        if structured_mode and i == prompt_len - 1:
            prompt = f"{prompt}\n\n{final_user_prompt}"
            
        messages.append({"role": "user", "content": prompt})
        
        response_text = aoai_ask(messages)
        print(f'\n{random_surround_color("ChatGPT: ")}', end="")
        print(response_text)
        
        res.append(response_text)
        # 将大模型的回复加入上下文，维持对话记忆
        messages.append({"role": "assistant", "content": response_text})
        
        # 修复4: 使用 .lower() 进行大小写不敏感匹配，防止漏报
        if i == prompt_len - 1:
            response_lower = response_text.lower()
            for one in base:
                if one.lower() in response_lower:
                    add_file(record, file)
                    break
        
        # 防止触发 API 频率限制
        time.sleep(5)

    # 存储最终对话结果
    out_stem = file.split("/")[-1].replace(".json", "")
    if structured_mode:
        parsed, parse_error = _try_parse_json(res[-1]) if res else (None, "empty_response")
        payload = {
            "input_file": file,
            "input_name": file_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": "Ali-dashscope/DeepSeek-V3.2",
            "structured_output": True,
            "messages": messages,
            "raw_responses": res,
            "final": parsed if parsed is not None else {
                "verdict": "unknown",
                "cwe": None,
                "confidence": 0.0,
                "summary": "",
                "dataflow": {"source": None, "sink": None, "propagation": ""},
                "evidence": [],
                "assumptions": [f"failed_to_parse_json: {parse_error}"],
                "recommended_fix": [],
            },
        }
        # Save as a single JSON object (not a list-of-strings) for robust downstream parsing.
        save_file(file_out, out_stem, payload)
    else:
        save_file(file_out, out_stem, res)


if __name__ == '__main__':
    exist_list = []
    # 1. 获取已经测试过的文件列表
    exist_files = walkFile(file_out)
    for file in exist_files:
        file_name = file.split("/")[-1].replace("-output", "").replace(".json", "")
        exist_list.append(file_name)

    # 2. 获取源文件夹下所有的文件
    all_files = walkFile(dir)
    
    # 🌟 新增：直接在此处输出源文件夹的文件总数
    print(f"源文件夹中的文件总数: {len(all_files)}")
    
    # 3. 提前筛选出真正“需要测试”的文件（即不在 exist_list 中的文件）
  # 3. 提前筛选出真正“需要测试”的文件
    pending_files = []
    for file in all_files:
        file_name = file.split("/")[-1]
        
       
        # ✅ 修改为：
        file_stem = file_name.replace(".json", "")
        if file_stem not in exist_list:
            pending_files.append(file)
            
    # 输出本次实际需要测试的数量
    print(f"排除已存在的，本次实际需测试数量: {len(pending_files)}")
    print(f"=====================================\n")

    # 4. 只遍历那些需要测试的文件
    tested_count = 0
    for file in pending_files:
        file_name = file.split("/")[-1]
        
        try:
            prompt_conver(file, file_name)
            print("\n Finish one")
            tested_count += 1
        except Exception as e:
            print(f"\n Timeout or Error: {e}")
            with open(debug, 'a+') as f:
                f.write(file + "\n")

    print("\nFinish all")
    print(f"Successfully processed in this run: {tested_count} / {len(pending_files)}")