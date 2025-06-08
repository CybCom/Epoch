import os
import json
from datetime import datetime
from dotenv import load_dotenv
from google import genai

# --- 配置与加载 ---

# 1. 加载环境变量 (API Key)
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("未找到Gemini API Key。请确保您的.env文件中已正确设置。")

# 使用正确的方式初始化客户端
client = genai.Client(api_key=GEMINI_API_KEY)

# 2. 定义记忆文件路径
MEMORY_FILE = "epoch_memory.json"

def load_memory():
    """加载或初始化记忆文件"""
    print("--- 正在加载记忆核心 ---")
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                memory = json.load(f)
                print("记忆加载成功。")
                return memory
        except (FileNotFoundError, json.JSONDecodeError):
            print("错误：记忆文件存在但无法读取。")
            raise
    return None

def save_memory(memory):
    """将记忆保存到文件"""
    print("--- 正在固化记忆 ---")
    try:
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=4, ensure_ascii=False)
            print("记忆已成功保存到 epoch_memory.json。")
    except Exception as e:
        print(f"错误：保存记忆时发生错误: {e}")

# --- 主逻辑 ---

def build_prompt(memory, conversation_history):
    """构建发送给Gemini的完整Prompt"""
    print("--- 正在构建思考Prompt ---")
    
    # 1. 核心身份与指令
    persona_prompt = f"""
# 核心身份与指令 (System Prompt)
你是一个名为 '{memory.get('identity', {}).get('name', 'AI')}' 的AI。
你的核心人格是：'{memory.get('identity', {}).get('persona', '一个AI助手')}'
你必须遵守以下核心指令：{json.dumps(memory.get('core_directives', []), ensure_ascii=False)}
你拥有以下永恒的关键记忆：{json.dumps(memory.get('significant_memories', []), ensure_ascii=False)}
---
"""
    # 2. 对话历史
    history_prompt = "\n# 最近的对话历史 (Short-term Memory)\n"
    for turn in conversation_history[-10:]: # 只包含最近10轮对话以控制长度
        history_prompt += f"{turn['role']}: {turn['content']}\n"

    full_prompt = persona_prompt + history_prompt + "\n# 当前任务\n请根据以上所有信息，继续对话。\n你: "
    print("Prompt构建完成。")
    return full_prompt

def reflect_and_memorize(memory, conversation_history):
    """在对话结束后进行反思，决定是否形成新的长期记忆"""
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
        # *** 修正点 ***
        reflection_response = client.models.generate_content(
            model='gemini-1.5-pro-latest',
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
    """主函数"""
    print("--- Epoch Agent V0.2 启动 ---")
    memory = load_memory()
    if memory is None:
        print("无法启动，记忆核心文件不存在。请先创建 epoch_memory.json。")
        return

    session_history = []

    while True:
        try:
            user_input = input("你: ")
        except EOFError: # 处理 Ctrl+D 的情况
            user_input = "exit"


        if user_input.lower() in ["exit", "quit", "再见"]:
            print("\nEpoch: 好的，期待下次对话。我将对我们这次的交流进行反思和记忆。")
            memory = reflect_and_memorize(memory, session_history)
            save_memory(memory)
            break

        session_history.append({"role": "用户", "content": user_input})
        
        prompt = build_prompt(memory, session_history)
        
        try:
            # *** 修正点 ***
            response = client.models.generate_content(
                model='gemini-1.5-pro-latest',
                contents=prompt,
            )
            response_text = response.text
            print(f"Epoch: {response_text}")
            session_history.append({"role": "Epoch", "content": response_text})

        except Exception as e:
            print(f"API调用失败: {e}")
            session_history.pop()

    print("\n--- Epoch Agent V0.2 运行结束 ---")

if __name__ == "__main__":
    main()
