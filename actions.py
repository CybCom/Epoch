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
    

# 在actions.py的imports中加入
import requests
from bs4 import BeautifulSoup

# 在actions.py的工具集部分，添加新函数
def browse_website(url: str) -> str:
    """
    访问一个给定的URL，并返回其网页的主要文本内容。
    这是Epoch的“深度视觉”。
    """
    print(f"--- [工具] 正在浏览网页: {url} ---")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # 如果请求失败则抛出异常
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 提取所有段落<p>标签的文本，这是最常见的文本容器
        paragraphs = soup.find_all('p')
        main_text = "\n".join([p.get_text() for p in paragraphs])
        
        if not main_text:
            return "无法从该网页提取主要的文本内容，可能是一个非文章类的页面。"
            
        return main_text[:4000] # 返回最多4000个字符以避免过长
    except Exception as e:
        return f"浏览网页时发生错误: {e}"    
    

# 在actions.py中添加
def scan_input_directory() -> str:
    """
    扫描指定的“输入”目录，并列出其中的所有文件名。
    这是Epoch感知新文件的主要方式。
    """
    input_dir = "input_files" # 我们约定一个目录名
    print(f"--- [工具] 正在扫描输入目录: {input_dir} ---")
    
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
        return f"输入目录 '{input_dir}' 已创建。当前为空。"
    
    files = os.listdir(input_dir)
    if not files:
        return f"输入目录 '{input_dir}' 当前为空。"
    
    return f"在输入目录 '{input_dir}' 中发现以下文件: {', '.join(files)}"    

