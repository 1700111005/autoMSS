"""
输入输出过程
项目架构
项目部署
demo

"""


async def classify_model(query: str = Body(..., description="用户输入")):
    """
    实现微调模型的调用，完成对五元组的初次分类
    """
    url = 'http://18.237.31.179:8000/'
    # 请求头
    headers = {
        'Content-Type': 'application/json'}

    data = {
        "prompt": query
    }
    # 将Python字典转换为JSON字符串
    json_data = json.dumps(data)
    # 发送POST请求
    response = requests.post(url, headers=headers, data=json_data)
    response = response.json()
    answer_6b, bigclass = response["history"][0][0].split(" ")
    # answer_6b=PROMPT3(response['response'])

    print(answer_6b)
    return answer_6b, bigclass