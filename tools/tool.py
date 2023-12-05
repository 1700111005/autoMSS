from langchain.agents import tool
from tools.IP_action import *
username = 'root'
password = '12345678?'

@tool("tool1")
def check_files(text:str) -> str:
    """
        这个工具只能在检查源 IP 服务器是否会在路径下⽣成临时⽂件的时候使用\
        输入应该总是一个字符串格式的ip服务器，\
    """
    is_temp_files = check_temp_files(text, username, password)
    return f"存在临时文件: {is_temp_files}"

@tool("tool2")
def check_kworker(text:str) -> str:
    """
        这个工具只能在检查源 IP 服务器进程中是否存在 kworker 关键字进程的时候使用\
        输入应该总是一个字符串格式的ip服务器，\
    """
    is_kworker = check_kworker_process(text, username, password)
    return f"{text}存在kworker进程: {is_kworker}"


@tool("tool3")
def check_2599(text: str) -> str:
    """
        这个工具只能在判断访问端ip服务器端口是否为2599的时候使用\
        输入应该总是一个字符串格式的ip服务器，\
    """
    is_port_2599 = check_port_2599(text, username, password)
    return f"目标IP端口为2599: {is_port_2599}"

@tool("tool4")
def check_behavior(text: str) -> str:
    """
        这个 工具 只能 在判断源ip服务器是否存在恶意行为的时候使用\
        输入应该总是一个字符串格式的ip服务器，\
    """
    malicious_behavior = check_malicious_behavior(text, username, password)
    return f"源IP地址恶意行为: {malicious_behavior}"

@tool("tool5")
def get_assests(text: str) -> str:
    """
        这个工具只能在获取源 IP 服务器资产信息的时候使用\
        输入应该总是一个字符串格式的ip服务器，\
    """
    # assests = ip_assests(text)
    # return str(assests)
    return "11111"

