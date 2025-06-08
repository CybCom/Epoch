# /home/epoch/Epoch/actions.py

import os
import requests # 使用requests库来发送HTTP请求
from duckduckgo_search import DDGS

# --- 工具集 ---

def search_web(query: str, max_results: int = 5) -> str:
    """
    使用DuckDuckGo进行网络搜索。
    """
    print(f"--- [工具] 正在执行网络搜索: {query} ---")
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
            if not results:
                return "网络搜索没有返回任何结果。"
            
            formatted_results = "\n\n".join(
                [f"来源: {r['href']}\n标题: {r['title']}\n摘要: {r['body']}" for r in results]
            )
            return formatted_results
    except Exception as e:
        error_message = f"网络搜索时发生错误: {e}"
        if "Ratelimit" in str(e):
            error_message += "\n提示：这可能是由于访问频率过高。建议等待一段时间再试。"
        return error_message

def send_notification(title: str, message: str) -> str:
    """
    *** 已重构 ***
    使用 ntfy.sh 发送一条推送通知。
    这是Epoch的“声音”。
    """
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        return "错误：NTFY_TOPIC 未在.env文件中配置。"
        
    print(f"--- [工具] 正在发送通知到ntfy主题: {topic} ---")
    
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode('utf-8'), # 消息正文
            headers={ "Title": title.encode('utf-8') } # 标题
        )
        return f"通知已成功发送至主题'{topic}'。"
    except Exception as e:
        return f"发送通知时发生严重错误: {e.__class__.__name__}: {e}"


def read_file(filepath: str) -> str:
    """
    读取指定文件的内容。
    """
    print(f"--- [工具] 正在读取文件: {filepath} ---")
    base_dir = os.path.abspath(os.path.dirname(__file__))
    target_path = os.path.abspath(os.path.join(base_dir, filepath))

    if not target_path.startswith(base_dir):
        return "错误：出于安全考虑，禁止访问项目目录以外的文件。"

    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"错误：文件 '{filepath}' 未找到。"
    except Exception as e:
        return f"读取文件时发生错误: {e}"