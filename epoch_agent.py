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
client = genai.Client(api_key=GEMINI_API_KEY)

# 2. 定义记忆文件路径
MEMORY_FILE = "epoch_memory.json"

def load_memory():
    """加载记忆文件"""
    print("--- 正在加载记忆核心 ---")
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            memory = json.load(f)
            print("记忆加载成功。")
            return memory
    except FileNotFoundError:
        print("警告：未找到记忆文件。将使用空记忆。")
        return {} # 在未来，这里可以创建一个默认的记忆结构
    except json.JSONDecodeError:
        print("错误：记忆文件格式不正确。")
        raise

# --- 主逻辑 ---

def build_prompt(memory, user_input):
    """构建发送给Gemini的完整Prompt"""
    print("--- 正在构建思考Prompt ---")
    
    # 将记忆核心转换为易于模型理解的文本
    persona_prompt = f"""
# 核心身份与指令 (System Prompt)
你是一个名为 '{memory.get('identity', {}).get('name', 'AI')}' 的AI。
你的核心人格是：'{memory.get('identity', {}).get('persona', '一个AI助手')}'
你必须遵守以下核心指令：{json.dumps(memory.get('core_directives', []), ensure_ascii=False)}
你拥有以下关键记忆：{json.dumps(memory.get('significant_memories', []), ensure_ascii=False)}
---
"""
    
    # 组合成最终的prompt
    # 在未来，这里会加入对话历史
    full_prompt = persona_prompt + f"\n# 用户当前的请求\n用户: {user_input}\n你: "
    print("Prompt构建完成。")
    return full_prompt


def main():
    """主函数"""
    print("--- Epoch Agent V0.1 启动 ---")
    memory = load_memory()
    
    # 模拟一次用户交互
    user_input = "你好，Epoch。请介绍一下你自己，并告诉我你记得什么。"
    
    prompt = build_prompt(memory, user_input)
    
    print("\n--- 正在与Gemini API通信 ---")
    # print("\n--- 发送的完整Prompt如下 ---") # 调试时可以取消注释
    # print(prompt)
    # print("--------------------------")
    
    # 调用API
    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro-preview-06-05',
            contents=prompt,
        )
        print("--- 已收到Gemini的回复 ---")
        
        # 打印结果
        print("\n=== Epoch的回应 ===\n")
        print(response.text)
        print("\n====================\n")
        
    except Exception as e:
        print(f"API调用失败: {e}")

    print("--- Epoch Agent V0.1 运行结束 ---")

if __name__ == "__main__":
    main()
    