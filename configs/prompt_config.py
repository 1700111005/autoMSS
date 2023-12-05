# 实现使用工具的prompt
agents_prompt = open('./docs/prompt/Utilization_Attacks_prompt', 'r', encoding='utf-8').read()
# 实现最后文本生成的prompt
get_docs_prompt = open('./docs/prompt/Generate_Documentation_prompt', 'r', encoding='utf-8').read()

# print(agents_prompt)
#自定义prompt，用于查询知识库
PROMPT = """<指令>回答要简洁不能有多余的内容</指令>

<已知信息>{{ context }}</已知信息>

<问题>{{ question }}</问题>"""