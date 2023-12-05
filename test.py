import re
import zhipuai
import time
import os
query_new="""
 第一步：获取攻击类型

攻击类型一：普通木马攻击
攻击类型二：emp3r0r 木马攻击

第二步：整理研判流程

攻击类型一：普通木马攻击
1. 判断源 IP 服务器资产信息
2. 判断源 IP 服务器是否存在恶意行为
3. 判断源 IP 服务器是否存在恶意 web 攻击日志信息
4. 判断目标 IP 地址情报信息
5. 木马文件分析

攻击类型二：emp3r0r 木马攻击
1. 判断目标 IP 端口是否为 2599
2. 判断源 IP 服务器进程中是否存在 kworker 关键字进程
3. 判断源 IP 服务器是否会在sr/share/bash-completion/completions/helpers/路径下生成临时文件

第三步：选择合适的工具进行工作

攻击类型一：普通木马攻击
1. 研判流程一：判断源 IP 服务器资产信息
Thought: 需要获取源 IP 服务器的资产信息
Action: 使用 tool5
Action Input: 输入源 IP 服务器地址 [172.24.158.39]

2. 研判流程二：判断源 IP 服务器是否存在恶意行为
Thought: 需要判断源 IP 服务器是否存在恶意行为
Action: 使用 tool4
Action Input: 输入源 IP 服务器地址 [172.24.158.39]

3. 研判流程三：判断源 IP 服务器是否存在恶意 web 攻击日志信息
Thought: 需要判断源 IP 服务器是否存在恶意 web 攻击日志信息
Action: 无适合的工具

4. 研判流程四：判断目标 IP 地址情报信息
Thought: 需要获取目标 IP 地址的情报信息
Action: 无适合的工具

5. 研判流程五：木马文件分析
Thought: 需要分析木马文件
Action: 使用 tool1
Action Input: 输入源 IP 服务器地址 [172.24.158.39]

攻击类型二：emp3r0r 木马攻击
1. 研判流程一：判断目标 IP 端口是否为 2599
Thought: 需要判断目标 IP 端口是否为 2599
Action: 使用 tool3
Action Input: 输入源 IP 服务器地址 [172.24.158.39]

2. 研判流程二：判断源 IP 服务器进程中是否存在 kworker 关键字进程
Thought: 需要判断源 IP 服务器进程中是否存在 kworker 关键字进程
Action: 使用 tool2
Action Input: 输入源 IP 服务器地址 [172.24.158.39]

3. 研判流程三：判断源 IP 服务器是否会在/usr/share/bash-completion/completions/helpers/路径下生成临时文件
Thought: 需要判断源 IP 服务器是否会在指定路径下生成临时文件
Action: 使用 tool1
Action Input: 输入源 IP 服务器地址 [172.24.158.39]
"""

#
# process_list=re.findall("第二步.*?[：,:].*?\\n([\s\S]*?)\\n\\n第三步",query_new)
# # process_listq=re.findall("([\s\S]*?)\\n\\n",query_new)
# # for item in process_listq:
# #     print(item)
# #     print("*"*100)
# tools=re.findall("第三步.*?[：,:].*?\\n([\s\S]*?)$",query_new)[0]
# use_tools=tools.split("\n\n")
#
# # print(re.findall("Action Input\s*\d*\s*:\s*\d*\s*\[(.*?)]",use_tools[0]))
# # print(process_list)
# for item in use_tools:
#     print(item)
#     print("*" * 100)
#
#
#
# # print(use_tools)
# tools_dict={}
# tools_not="缺失的工具:"
# for item in use_tools:
#     if "Action Input" in item:
#         # Thought=re.findall("Thought\s*\d*\s*:([\s\S]*?)\\n",item)[0]
#         Action=re.findall("Action\s*[：,:]\s*[\u4e00-\u9fa5]*\s*([\s\S]*?)\s*\\n",item)[0]
#         print(Action)
#         Action_Input=re.findall("Action Input[：,:].*?\s\[(.*?)]",item)[0]
#         print(Action_Input)
#         tools_dict[Action]=Action_Input
#     else:
#         Thought = re.findall("Thought\s*:\s([\s\S]*?)\\n", item)[0]
#         tools_not+=("\n"+Thought)
#
# print(tools_dict)
# print(tools_not)
t=time.localtime()
# print(t.tm_year, t.tm_mon, t.tm_mday,t.tm_hour,t.tm_min,t.tm_sec)
data=str(t.tm_mon)+"月"+str(t.tm_mday)+"日"
data1=str(t.tm_hour)+ str(t.tm_min)+str( t.tm_sec)
if not os.path.exists(f'../../docs/{data}'):
    os.mkdir(f'./docs/{data}')
with open(f'./docs/{data}/{data1}.txt', 'w',
          encoding="utf-8") as f:
    f.write("answer")