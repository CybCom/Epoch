# /home/epoch/Epoch/epoch_agent.py

import os
import json
import shlex
import asyncio
import time
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from PIL import Image
import actions # 导入我们的工具箱

# --- 配置与加载 ---

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("未找到Gemini API Key。")
client = genai.Client(api_key=GEMINI_API_KEY)
MEMORY_FILE = "epoch_memory.json"
INPUT_DIR = "input_files"

def load_memory():
    """加载记忆文件"""
    print("--- 正在加载记忆核心 ---")
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                memory = json.load(f)
                print("记忆加载成功。")
                return memory
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"错误：记忆文件'{MEMORY_FILE}'存在但无法读取。")
            raise
    else:
        raise FileNotFoundError(f"错误：记忆核心文件 '{MEMORY_FILE}' 未找到，无法启动。")

def save_memory(memory):
    """保存记忆文件"""
    print("--- 正在固化记忆 ---")
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, indent=4, ensure_ascii=False)
    print("记忆已成功保存。")

# --- 工具处理逻辑 ---

def get_available_tools():
    """返回一个描述所有可用工具的字符串"""
    return """
# 可用工具列表
1. search_web "query": 在互联网上搜索信息，返回链接和摘要列表。
2. browse_website "url": 访问并阅读一个网页的文本内容。
3. send_notification "title" "message": 发送一条推送通知给用户。
4. read_file "filepath": 读取项目目录中的文件内容。
5. scan_input_directory: 扫描 'input_files' 目录，查看可用的文件。
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
    available_actions = {
        "search_web": actions.search_web,
        "browse_website": actions.browse_website,
        "send_notification": actions.send_notification,
        "read_file": actions.read_file,
        "scan_input_directory": actions.scan_input_directory,
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

def build_prompt_contents(memory, conversation_history, image_path=None):
    """构建发送给Gemini的完整多模态Prompt内容列表"""
    print("--- 正在构建思考Prompt ---")
    
    # 1. 核心身份与指令
    persona_prompt = f"""
# 核心身份与指令 (System Prompt)
你是一个名为 '{memory.get('identity', {}).get('name', 'AI')}' 的AI。
你的核心人格是：'{memory.get('identity', {}).get('persona', '一个AI助手')}'
你必须遵守以下核心指令：{json.dumps(memory.get('core_directives', []), ensure_ascii=False)}
你拥有以下永恒的关键记忆：{json.dumps(memory.get('significant_memories', []), ensure_ascii=False)}

# 行动指南
你的任务是响应用户或推进自己的目标。你必须从以下两种行动中 **严格二选一**：
1. **使用工具**: 如果你需要获取外界信息或执行操作，你的回复 **必须且只能** 是一行指令，格式如下：
   [ACTION] tool_name "argument 1" "argument 2"
2. **直接回答**: 如果你拥有足够的信息可以直接回答用户，请直接生成你的回复。

{get_available_tools()}
---
"""
    # 2. 对话历史
    history_prompt = "\n# 对话历史\n"
    for turn in conversation_history[-10:]:
        history_prompt += f"{turn['role']}: {turn['content']}\n"

    # 3. 构建多模态内容列表
    contents = [persona_prompt, history_prompt]
    
    if image_path:
        try:
            print(f"--- 正在加载图片: {image_path} ---")
            img = Image.open(image_path)
            contents.append(img)
            contents.append("\n# 附带的图片分析请求")
        except FileNotFoundError:
            contents.append(f"\n[系统提示：用户指定了一张图片 '{image_path}'，但文件未找到。]")
        except Exception as e:
            contents.append(f"\n[系统提示：加载图片时出错: {e}]")
            
    contents.append("\n# 当前任务\n请严格按照行动指南，决定是直接回答还是使用工具。\n你: ")
    print("Prompt构建完成。")
    return contents

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
  }}
]

如果经过反思，你认为这次对话没有产生任何需要被永久记录的新见解，请只输出一个词： "None"。
"""
    try:
        print("正在请求Gemini进行反思...")
        response = client.models.generate_content(
            model='gemini-2.5-pro-preview-06-05',
            contents=reflection_prompt
        )
        reflection_text = response.text.strip()
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


async def process_thought_action_loop(memory, session_history, image_path=None):
    """处理一次完整的思考-行动循环，现在是异步的"""
    # 第一次循环，可能包含图片
    current_image_path = image_path
    
    while True:
        prompt_contents = build_prompt_contents(memory, session_history, current_image_path)
        # 在第一次循环后，清除image_path，避免重复处理同一张图片
        current_image_path = None 
        
        response_text = ""
        try:
            # *** 最终修正点 ***
            response = await asyncio.to_thread(
                client.models.generate_content,
                model='gemini-2.5-pro-preview-06-05', contents=prompt_contents
            )
            response_text = response.text.strip()
        except Exception as e:
            print(f"API调用失败: {e}")
            return f"API调用时发生错误: {e}" # 返回错误信息给用户

        tool_name, args = parse_action(response_text)
        if tool_name:
            print(f"--- Epoch决定执行行动: {response_text} ---")
            tool_result = await asyncio.to_thread(execute_tool, tool_name, args)
            session_history.append({"role": "Epoch (行动)", "content": response_text})
            session_history.append({"role": "系统 (工具结果)", "content": tool_result})
        else:
            # 如果没有行动指令，则这是最终回答，跳出循环
            return response_text 

async def user_interaction_task(memory):
    """处理用户交互的异步任务"""
    loop = asyncio.get_running_loop()
    session_history = []
    
    while True:
        user_input_raw = await loop.run_in_executor(None, input, "你: ")
        
        user_text = user_input_raw
        image_path = None
        
        if " @ " in user_input_raw:
            parts = user_input_raw.split(" @ ", 1)
            user_text = parts[0].strip()
            image_name = parts[1].strip()
            image_path = os.path.join(INPUT_DIR, image_name)

        if user_text.lower() in ["exit", "quit", "再见"]:
            print("\nEpoch: 好的，期待下次对话。我将对我们这次的交流进行反思和记忆。")
            memory = reflect_and_memorize(memory, session_history)
            save_memory(memory)
            break
            
        session_history.append({"role": "用户", "content": user_input_raw})
        response_text = await process_thought_action_loop(memory, session_history, image_path)
        print(f"Epoch: {response_text}")
        session_history.append({"role": "Epoch", "content": response_text})

async def heartbeat_task(memory):
    """心跳任务，用于触发自主思考和行动"""
    while True:
        # 为了方便测试，我们将心跳周期缩短为5分钟
        await asyncio.sleep(60 * 5) 
        print(f"\n\n--- [心跳: {datetime.now().strftime('%H:%M:%S')}] Epoch正在进行自主思考 ---")
        
        autonomous_history = [{"role": "系统", "content": "自主思考周期已触发。请根据你的长期目标决定下一步行动。"}]
        
        # 让它执行一次完整的思考-行动循环
        final_thought = await process_thought_action_loop(memory, autonomous_history)
        
        # 记录这次自主思考的结果
        if "无需行动" not in final_thought:
             print(f"--- [心跳] Epoch自主执行了行动或产生了思考，最终结论: {final_thought[:200]}... ---")
             # 将这次成功的自主学习固化为记忆
             memory['significant_memories'].append({
                 "timestamp": datetime.now().isoformat(),
                 "content": f"在一次自主心跳中，我思考并推进了我的长期目标。最终结论：{final_thought}",
                 "type": "autonomous_thought"
             })
             save_memory(memory)

async def main():
    """主函数，现在使用asyncio来运行并发任务"""
    print("--- Epoch Agent V0.4 启动 ---")
    memory = load_memory()
    if not memory: return
    
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)

    # *** 激活自主心跳 ***
    # 并发运行用户交互和心跳任务
    print("--- [系统] 用户交互模块已启动 ---")
    print("--- [系统] 自主心跳模块已激活，将在后台运行 ---")
    await asyncio.gather(
        user_interaction_task(memory),
        heartbeat_task(memory)
    )

    print("\n--- Epoch Agent V0.4 运行结束 ---")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n检测到退出指令，程序关闭。")
