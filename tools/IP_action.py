import paramiko

# SSH连接配置
def establish_ssh_connection(ip_address, username, password):
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ip_address, username=username, password=password)
        return ssh_client
    except Exception as e:
        print(f"SSH连接失败: {str(e)}")
        return None

# 判断源IP地址是否存在恶意行为，agent流程step2
def check_malicious_behavior(ip_address, username, password):
    ssh_client = establish_ssh_connection(ip_address, username, password)
    if not ssh_client:
        return False

    # 判断代理进程
    proxy_count = check_proxy_process(ssh_client)
    # 判断恶意命令
    malicious_commands = check_malicious_commands(ssh_client)

    ssh_client.close()

    return proxy_count >= 2 or malicious_commands

# 检查是否存在代理进程，agent流程step2.1
def check_proxy_process(ssh_client):
    try:
        stdin, stdout, stderr = ssh_client.exec_command("ps aux | grep sock5")
        processes = stdout.read().decode('utf-8')
        count = processes.count("sock5")
        '''
        if (count >= 2):
            print(f"未发现代理进程")
        else:
            print(f"发现代理进程！")   
        '''
        return count >= 2

    except Exception as e:
        print(f"检查代理进程时出错: {str(e)}")
        return False

# 检查是否存在恶意命令，agent流程step2.2
def check_malicious_commands(ssh_client):
    try:
        stdin, stdout, stderr = ssh_client.exec_command("history")
        command_history = stdout.read().decode('utf-8')
        return "nc" in command_history or "cat /etc/passwd" in command_history or "cat /etc/shadow" in command_history
    except Exception as e:
        print(f"检查恶意命令时出错: {str(e)}")
        return False

# 判断目标IP端口是否为2599，agent流程step6
def check_port_2599(ip_address, username, password):
    ssh_client = establish_ssh_connection(ip_address, username, password)
    if not ssh_client:
        return False

    try:
        stdin, stdout, stderr = ssh_client.exec_command("netstat -antp")
        netstat_output = stdout.read().decode('utf-8')
        ssh_client.close()
        return "2599" in netstat_output
    except Exception as e:
        print(f"检查端口2599时出错: {str(e)}")
        return False

# 检查是否存在kworker进程，agent流程step7
def check_kworker_process(ip_address, username, password):
    ssh_client = establish_ssh_connection(ip_address, username, password)
    if not ssh_client:
        return False
    try:
        stdin, stdout, stderr = ssh_client.exec_command("ps aux | grep kworker")
        kworker_processes = stdout.read().decode('utf-8')
        ssh_client.close()
        return "kworker" in kworker_processes
    except Exception as e:
        print(f"检查kworker进程时出错: {str(e)}")
        return False

# 检查是否在指定路径下生成临时文件，agent流程step8
def check_temp_files(ip_address, username, password, path="/usr/share/bash-completion/completions/helpers/"):
    ssh_client = establish_ssh_connection(ip_address, username, password)
    if not ssh_client:
        return False

    try:
        stdin, stdout, stderr = ssh_client.exec_command(f"ls {path}")
        file_list = stdout.read().decode('utf-8')
        ssh_client.close()
        return "ssh-" in file_list
    except Exception as e:
        print(f"检查临时文件时出错: {str(e)}")
        return False

if __name__ == "__main__":
    # 你可以在这里进行测试
    ip_address = 'xxxxx'
    username = 'root'
    password = 'xxxxx'

    malicious_behavior = check_malicious_behavior(ip_address, username, password)
    is_port_2599 = check_port_2599(ip_address, username, password)
    is_kworker = check_kworker_process(ip_address, username, password)
    is_temp_files = check_temp_files(ip_address, username, password)

    print(f"源IP地址恶意行为: {malicious_behavior}")
    print(f"目标IP端口为2599: {is_port_2599}")
    print(f"存在kworker进程: {is_kworker}")
    print(f"存在临时文件: {is_temp_files}")
