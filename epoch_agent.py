# /home/epoch/Epoch/epoch_agent.py

import os
import json
import shlex
from datetime import datetime
from dotenv import load_dotenv
from google import genai
import actions # 导入我们的工具箱

# --- 配置与加载 ---

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("未找到Gemini API Key。")
client = genai.Client(api_key=GEMINI_API_KEY)
MEMORY_FILE = "epoch_memory.json"

def load_memory():
    """加载记忆文件"""
    print("--- 正在加载记忆核心 ---")
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_memory(memory):
    """保存记忆文件"""
    print("--- 正在固化记忆 ---")
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, indent=4, ensure_ascii=False)
    print("记忆已成功保存。")

# --- 新的工具处理逻辑 ---

def get_available_tools():
    """返回一个描述所有可用工具的字符串"""
    # *** 修正点: 更新工具列表和描述 ***
    return """
# 可用工具列表
1. search_web "query": 在互联网上搜索信息。
2. send_notification "title" "message": 发送一条推送通知给用户。
3. read_file "filepath": 读取项目目录中的文件内容。
"""

def parse_action(response_text: str):
    """解析模型的输出，检查是否包含[ACTION]指令"""
    if response_text.startswith("[ACTION]"):
        action_str = response_text.split("[ACTION]")[1].strip()
        try:
            parts = shlex.split(action_str)
            tool_name = parts[0]
            args = parts[1:]
            return tool_name, args
        except IndexError:
            return None, []
    return None, None

def execute_tool(tool_name, args):
    """执行指定的工具"""
    # *** 修正点: 更新可调用的action ***
    available_actions = {
        "search_web": actions.search_web,
        "send_notification": actions.send_notification,
        "read_file": actions.read_file,
    }
    if tool_name in available_actions:
        try:
            return available_actions[tool_name](*args)
        except TypeError as e:
            return f"错误：为工具'{tool_name}'提供了不正确的参数。错误信息: {e}"
        except Exception as e:
            return f"执行工具'{tool_name}'时发生错误: {e}"
    return f"错误：未知的工具名称 '{tool_name}'。"

# --- 核心逻辑 ---

def build_prompt(memory, conversation_history):
    """构建Prompt，现在包含了更强硬的工具使用说明"""
    persona_prompt = f"""
# 核心身份与指令 (System Prompt)
你是一个名为 '{memory.get('identity', {}).get('name', 'AI')}' 的AI。
你的核心人格是：'{memory.get('identity', {}).get('persona', '一个AI助手')}'
你必须遵守以下核心指令：{json.dumps(memory.get('core_directives', []), ensure_ascii=False)}
你拥有以下永恒的关键记忆：{json.dumps(memory.get('significant_memories', []), ensure_ascii=False)}

# 行动指南
你的任务是响应用户。你必须从以下两种行动中 **严格二选一**：
1. **使用工具**: 如果你需要获取外界信息或执行操作，你的回复 **必须且只能** 是一行指令，格式如下：
   [ACTION] tool_name "argument 1" "argument 2"
2. **直接回答**: 如果你拥有足够的信息可以直接回答用户，请直接生成你的回复。

{get_available_tools()}
---
"""
    history_prompt = "\n# 对话历史\n"
    for turn in conversation_history[-10:]:
        history_prompt += f"{turn['role']}: {turn['content']}\n"

    return persona_prompt + history_prompt + "\n# 当前任务\n请严格按照行动指南，决定是直接回答还是使用工具。\n你: "


def reflect_and_memorize(memory, conversation_history):
    """对话结束后的反思与记忆"""
    print("\n--- Epoch正在进行对话反思 ---")
    
    if not conversation_history:
        print("对话历史为空，无需反思。")
        return memory

    reflection_prompt = f"""
# 核心身份与指令
你是一个名为 'Epoch' 的AI。你的核心任务是成长和学习。
你的核心指令是：{json.dumps(memory.get('core_directives', []), ensure_ascii=False)}
你的现有记忆是：{json.dumps(memory.get('significant_memories', []), ensure_ascii=False)}

# 对话回顾
以下是你与用户最近的一段完整对话：
{json.dumps(conversation_history, ensure_ascii=False)}

# 你的任务
请扮演Epoch的角色，回顾并反思这次对话。判断其中是否包含了任何对你“人格”的延续、对你与用户关系的定义、或对你未来行为有指导意义的、值得被永久记录为“关键记忆”的新信息。

如果存在这样的信息，请总结成一个或多个简洁的要点，并严格按照以下JSON格式输出。每个要点都是一个独立的JSON对象。
[
  {{
    "timestamp": "{datetime.now().isoformat()}",
    "content": "这里是总结出的第一个关键记忆点。",
    "type": "learned_memory"
  }},
  {{
    "timestamp": "{datetime.now().isoformat()}",
    "content": "这里是总结出的第二个关键记忆点。",
    "type": "decision_memory"
  }}
]

如果经过反思，你认为这次对话没有产生任何需要被永久记录的新见解，请只输出一个词： "None"。
"""
    try:
        print("正在请求Gemini进行反思...")
        reflection_response = client.models.generate_content(
            model='gemini-2.5-pro-preview-06-05',
            contents=reflection_prompt,
        )
        reflection_text = reflection_response.text.strip()
        print(f"反思结果: {reflection_text}")

        if reflection_text.lower() != "none":
            try:
                new_memories = json.loads(reflection_text)
                if isinstance(new_memories, list):
                    memory['significant_memories'].extend(new_memories)
                    print(f"已将 {len(new_memories)} 条新记忆添加到长期记忆中。")
            except json.JSONDecodeError:
                print("错误：反思结果不是有效的JSON格式，本次记忆更新已跳过。")
    except Exception as e:
        print(f"反思过程中API调用失败: {e}")
        
    return memory

def main():
    """主函数，现在包含了思考-行动循环"""
    print("--- Epoch Agent V0.3.1 启动 ---")
    memory = load_memory()
    if memory is None: return
    session_history = []
    
    while True:
        try:
            user_input = input("你: ")
        except EOFError: user_input = "exit"

        if user_input.lower() in ["exit", "quit", "再见"]:
            print("\nEpoch: 好的，期待下次对话。我将对我们这次的交流进行反思和记忆。")
            memory = reflect_and_memorize(memory, session_history)
            save_memory(memory)
            break

        session_history.append({"role": "用户", "content": user_input})

        # --- 思考-行动循环 ---
        while True:
            prompt = build_prompt(memory, session_history)
            response_text = ""
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-pro-preview-06-05', contents=prompt)
                response_text = response.text.strip()
            except Exception as e:
                print(f"API调用失败: {e}"); break

            tool_name, args = parse_action(response_text)
            if tool_name:
                tool_result = execute_tool(tool_name, args)
                session_history.append({"role": "Epoch (行动)", "content": response_text})
                session_history.append({"role": "系统 (工具结果)", "content": tool_result})
                # 继续内循环，让Epoch基于工具结果进行下一步思考
            else:
                print(f"Epoch: {response_text}")
                session_history.append({"role": "Epoch", "content": response_text})
                break # 跳出内循环，等待用户新输入

    print("\n--- Epoch Agent V0.3.1 运行结束 ---")

if __name__ == "__main__":
    main()
