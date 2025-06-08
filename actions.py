# /home/epoch/Epoch/actions.py

import os
import smtplib
from email.mime.text import MIMEText
from duckduckgo_search import DDGS
import time

# --- 工具集 ---

def search_web(query: str, max_results: int = 5) -> str:
    """
    使用DuckDuckGo进行网络搜索，并处理频率限制问题。
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

def send_email(recipient: str, subject: str, body: str) -> str:
    """
    使用配置好的Outlook邮箱发送邮件。
    """
    print(f"--- [工具] 正在发送邮件给: {recipient} ---")
    sender_email = os.getenv("OUTLOOK_EMAIL")
    password = os.getenv("OUTLOOK_PASSWORD") 

    if not sender_email or not password:
        return "错误：发件人邮箱或密码未在.env文件中配置。"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient

    try:
        smtp_server = 'smtp-mail.outlook.com'
        smtp_port = 587
        print(f"--- [调试] 尝试连接到 {smtp_server}:{smtp_port} ---")
        
        # *** 修正点: 在创建SMTP实例时，明确指定local_hostname ***
        with smtplib.SMTP(smtp_server, smtp_port, local_hostname='localhost') as server:
            print("--- [调试] 连接成功，启动TLS... ---")
            server.starttls()
            print("--- [调试] TLS启动，正在登录... ---")
            server.login(sender_email, password)
            print("--- [调试] 登录成功，正在发送邮件... ---")
            server.sendmail(sender_email, [recipient], msg.as_string())
            print("--- [调试] 邮件已发送。 ---")
        return "邮件发送成功。"
    except Exception as e:
        return f"邮件发送时发生严重错误: {e.__class__.__name__}: {e}"


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
