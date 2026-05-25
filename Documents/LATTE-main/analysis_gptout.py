import json
import re
import os
from Utils import *

dir = "/home/user/Document/GPT_78_bad"

files = walkFile(dir)

result_file = "/home/user/Document/GPT_analysis/" + dir.split("/")[-1] + "_result.txt"

# 自动判断当前目录是漏洞数据集还是安全数据集
is_bad_dataset = "bad" in dir.lower()
is_good_dataset = "good" in dir.lower()

if not is_bad_dataset and not is_good_dataset:
    print("⚠️ 警告: 无法从路径中识别 'bad' 或 'good'，默认按 'bad' (漏洞文件) 处理。")
    is_bad_dataset = True

# 初始化统计指标
TP = 0  # 测出漏洞，实际也是漏洞
FN = 0  # 测成安全，实际是漏洞 (漏报)
TN = 0  # 测成安全，实际也是安全
FP = 0  # 测出漏洞，实际是安全 (误报)

no_list = []      # 记录被判定为 vulnerable 的文件
failed_list = []  # 新增：记录判定失败（分类错误）的文件

for file in files:
    try:
        raw_content = load_file(file)
        
        # 1. 尝试解析 JSON
        try:
            parsed_data = json.loads(raw_content)
        except (ValueError, TypeError):
            parsed_data = raw_content # 如果不是合法 JSON，保留纯文本做兜底

        is_vulnerable = False
        
        # 2. JSON 字典结构提取
        if isinstance(parsed_data, dict):
            if "final" in parsed_data:
                verdict = parsed_data.get("final", {}).get("verdict", "")
            else:
                verdict = parsed_data.get("verdict", "")
                
            if verdict == "vulnerable":
                is_vulnerable = True

        # 3. 列表结构提取 (兼容旧版)
        elif isinstance(parsed_data, list) and len(parsed_data) > 0:
            last_item = parsed_data[-1]
            parsed_data = str(last_item) 

        # 4. 文本正则兜底
        if not is_vulnerable and isinstance(parsed_data, str):
            prompt_lower = parsed_data.lower()
            if re.search(r'\byes\b', prompt_lower) or 'there is a potential vulnerability' in prompt_lower or '"verdict": "vulnerable"' in prompt_lower:
                is_vulnerable = True
        
        # 5. 更新混淆矩阵指标与失败记录
        file_name = file.split("/")[-1]
        if is_vulnerable:
            no_list.append(file_name)
            print(f"{file} !!!!!!!!!!!!!!!!!!! (Vulnerable)")
            
            if is_bad_dataset:
                TP += 1
            else:
                FP += 1
                failed_list.append(file_name) # 误报，判定失败
        else:
            print(f"{file} (Safe)")
            if is_bad_dataset:
                FN += 1
                failed_list.append(file_name) # 漏报，判定失败
            else:
                TN += 1
                
    except Exception as e:
        print(file + " - Error: " + str(e) + " !!!!!!!!!!!!!!!!!!!")

# 确保输出目录存在
os.makedirs(os.path.dirname(result_file), exist_ok=True)

with open(result_file, 'w') as f:
    f.write(f"--- 分析报告 ({'Bad/Vulnerable 集' if is_bad_dataset else 'Good/Safe 集'}) ---\n")
    f.write(f"总扫描文件数: {len(files)}\n")
    f.write(f"模型判定为漏洞(Vulnerable)数量: {len(no_list)}\n")
    f.write(f"模型判定为安全(Safe)数量: {len(files) - len(no_list)}\n\n")
    
    f.write("--- 混淆矩阵 (Metrics) ---\n")
    f.write(f"TP (真阳性 - 正确测出的漏洞): {TP}\n")
    f.write(f"FN (假阴性 - 漏报的漏洞): {FN}\n")
    f.write(f"TN (真阴性 - 正确确认的安全): {TN}\n")
    f.write(f"FP (假阳性 - 误报的安全): {FP}\n\n")
    
    # 新增：输出判定失败的文件列表
    f.write("--- 判定失败 (分类错误) 的文件列表 ---\n")
    if len(failed_list) == 0:
        f.write("无判定失败的文件，全部判断正确！\n\n")
    else:
        for value in failed_list:
            f.write(value + "\n")
    f.write("\n")

    f.write("--- 判定为 Vulnerable 的文件列表 ---\n")
    for value in no_list:
        f.write(value + "\n")

# --- 终端输出结果 ---
print("\n" + "="*40)
print(f"分析完成！共扫描 {len(files)} 个文件。")
print(f"当前数据集类型: {'🔴 Bad (漏洞集)' if is_bad_dataset else '🟢 Good (安全集)'}")
print("-" * 40)
print(f"TP (测出漏洞): {TP}")
print(f"FN (漏报安全): {FN}")
print(f"TN (确认安全): {TN}")
print(f"FP (误报漏洞): {FP}")
print(f"acc (准确率): {((TP + TN) / (TP + FN + TN + FP)) if (TP + FN + TN + FP) > 0 else 0}")
print(f"判定失败文件数: {len(failed_list)}")
print("="*40)
print(f"结果已详细保存至 {result_file}")