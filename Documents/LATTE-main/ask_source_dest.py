"""
OpenAI API (via Proxy/Hub)
=============

This module provides some official GPT API, which includes
1. OpenAI ChatCompletion API
2. OpenAI Completion API
3. OpenAI Embedding API
"""
import os
import sys
import time
import json
from datetime import datetime
from openai import OpenAI, APIConnectionError, RateLimitError, APIError

# Ensure local imports work regardless of current working directory.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Support both `Utils.py` and `utils.py`.
try:
    from Utils import * # noqa: F401,F403
except ImportError:
    from utils import * # type: ignore # noqa: F401,F403

dir="/home/user/Document/LATTE_Output/Potentially Vulnerable/CWE_78_bad"
file_out_content="/home/user/Document/content/cwe78bad/"


client = OpenAI(
    api_key="sk-353_hVaN4gkF5mJPnQnj3Q",
    base_url="https://xplt.sdu.edu.cn:4000/v1",
    timeout=60.0 
)

def aoai_ask(prompt, model="Ali-dashscope/DeepSeek-V3.2", temperature=0):
    knowledge_cutoff = "2025-09-01"
    current_date = datetime.now().strftime("%Y-%m-%d")

    if isinstance(prompt, str):
        system_prompt= f"You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible. Knowledge cutoff: {knowledge_cutoff} Current date: {current_date}"
        system_prompt = {"role":"system","content":system_prompt}
        new_prompt = {"role":"user","content":prompt}
        final_prompt = [system_prompt, new_prompt]
    elif isinstance(prompt, list):
        final_prompt = prompt
    else:
        raise TypeError("Expected a string as input") 

    # 优化 2：重构重试逻辑。使用循环替代臃肿的 try-except 嵌套
    max_retries = 3
    for attempt in range(max_retries):
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
            text = response.choices[0].message.content
            print(f"GPT ({model}): ", [text])
            return text
            
        except RateLimitError:
            print(f"⚠️ 触发限流 (尝试 {attempt+1}/{max_retries}). 睡眠 60 秒后重试...")
            time.sleep(60)
        except APIConnectionError:
            print(f"⚠️ 网络连接错误 (尝试 {attempt+1}/{max_retries}). 睡眠 5 秒后重试...")
            time.sleep(5)
        except Exception as e:
            # 捕获包括 Timeout 在内的其他所有 API 异常
            print(f"⚠️ API 请求异常 (尝试 {attempt+1}/{max_retries}) Detail: {repr(e)}")
            time.sleep(10)
            
    # 如果循环走完（3次全失败），抛出异常让外层捕获，跳过当前文件
    raise Exception(f"请求失败次数过多，已放弃当前 Prompt。")


def aoai_embedding(input_str, model="text-embedding-ada-002"):
    response = client.embeddings.create(
        input=input_str,
        model=model
    )
    embeddings = response.data[0].embedding
    return embeddings

def aoai_completion(new_prompt, model="text-davinci-003", temperature=0):
    response = client.completions.create(
        model=model,
        prompt=new_prompt,
        temperature=temperature,
        max_tokens=2040,
        top_p=0.5,
        frequency_penalty=0,
        presence_penalty=0,
        best_of=1,
        stop=None
    )

    text = response.choices[0].text
    print(f"GPT ({model}) ", [text])
    return text

if __name__ == "__main__":
    prompt_source = "Please use the function name to find the function that can directly receive external input or generate pseudo random number as the taint source in the taint analysis. Function names without semantic information are ignored. And output only in the form of [function name, external input corresponding parameters order or return value] without other description"
    prompt_sink = "For taint analysis, please use the function name to find the taint sink that may lead to vulnerabilities such as command hijacking, buffer overflow, format string, etc. Function names without semantic information are ignored. And output only in the form of [function name, parameter order corresponding to the vulnerability] without other description."
    
    exist_list_name = []
    exist_list_content = []

    exist_files = walkFile(file_out)
    for file in exist_files:
        file_name = file.split("/")[-1].replace("-srdst", "")
        exist_list_name.append(file_name)

    exist_files = walkFile(file_out_content)
    for file in exist_files:
        file_name = file.split("/")[-1].replace("-content", "")
        exist_list_content.append(file_name)

    files = walkFile(dir)
    print(f"DEBUG: 在输入目录中共找到 {len(files)} 个文件。")
    print(f"DEBUG: 已存在列表 exist_list_name 中有 {len(exist_list_name)} 个记录。")
    
    for file in files:
        file_name = file.split("/")[-1]
        
        if "CWE78" in file_name:
            if file_name in exist_list_name:
                print(f"[{file_name}] 已处理，跳过。")
                continue
                
            print(f"\n==== 开始处理: {file_name} ====")
            function = load_file(file)
            
            try:
                parsed_json = json.loads(function)
            except json.JSONDecodeError:
                print(f"❌ {file_name} JSON 解析失败，跳过。")
                continue
            
            # 处理可能存在的双重编码的字符串
            if isinstance(parsed_json, str):
                try:
                    parsed_json = json.loads(parsed_json)
                except json.JSONDecodeError:
                    pass
                
            # 根据解析出来的类型（字典还是列表）分别提取内容
            if isinstance(parsed_json, dict):
                function_list = str(list(parsed_json.keys()))
            elif isinstance(parsed_json, list):
                function_list = str(parsed_json)
            else:
                function_list = str(parsed_json)
                
            print("candidate function: " + function_list)
            
            # ---------------- 请求 Source ----------------
            prompt_source_final = prompt_source + function_list
            try:
                source = aoai_ask(prompt_source_final)
                print("✅ Finish source one")
            except Exception as e:
                # 优化 3：明确捕获 Exception，防止屏蔽 Ctrl+C，并打印出具体失败原因
                print(f"❌ {file_name} 请求 Source 失败: {e}，跳过此文件。")
                continue
                
            time.sleep(3) # 降低被封禁/限流的概率
            
            # ---------------- 请求 Sink ----------------
            prompt_sink_final = prompt_sink + function_list
            try:
                sink = aoai_ask(prompt_sink_final)
                print("✅ Finish sink one")
            except Exception as e:
                print(f"❌ {file_name} 请求 Sink 失败: {e}，跳过此文件。")
                continue
            
            # ---------------- 写入文件 ----------------
            output = [
                "Source: " + source + "; Sink: " + sink
            ]
            
            file_path = file_out + file_name.strip(".json") + "-srdst.json"
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(output, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"❌ 写入文件失败: {e}")
                
            time.sleep(5)

    print("\n🎉 Finish all")
