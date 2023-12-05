from fastapi import Body
from configs import VECTOR_SEARCH_TOP_K, SCORE_THRESHOLD, LLM_MODEL_130B, llm_model_dict, get_docs_prompt,agents_prompt,tools
from fastapi.responses import StreamingResponse
import asyncio
import requests
import time
import json
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.agents import LLMSingleActionAgent,AgentExecutor
from .utils import Agent_PromptTemplate,Agent_OutputParser
from langchain import LLMChain
from server.chat.utils import History, wrap_done
from langchain.prompts.chat import ChatPromptTemplate
from server.knowledge_base.kb_doc_api import search_docs
import os


def vulnerability_analysis(
        query: str = Body('2023/10/9 11:23 172.24.158.39:45676 180.215.5.133:2599  emp3r0r木马攻击 https中疑似存在emp3r0r恶意流量',
                          description="用户输入"),
        knowledge_base_name: str = Body("mss", description="知识库名称"),
        top_k: int = Body(VECTOR_SEARCH_TOP_K, description="匹配向量数"),
        score_threshold: float = Body(SCORE_THRESHOLD,
                                      description="知识库匹配阈值",
                                      ge=0, le=1),
        temperature1: int = Body(0, description="向量库问答的模型温度", ge=0, le=1),
        temperature2: int = Body(0, description="使用工具的模型温度", ge=0, le=1),
        model_name: str = Body(LLM_MODEL_130B, description="LLM 模型名称"),
):
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
        answer_6b,bigclass = response["history"][0][0].split(" ")['response']
        # answer_6b=PROMPT3(response['response'])

        print(answer_6b)
        return answer_6b,bigclass


    async def use_tools(query: str, big_class,knowledge_base_name:str,model_name: str = model_name):
        model = ChatOpenAI(
            streaming=True,
            verbose=True,
            openai_api_key=llm_model_dict[model_name]["api_key"],
            openai_api_base=llm_model_dict[model_name]["api_base_url"],
            model_name=model_name,
            openai_proxy=llm_model_dict[model_name].get("openai_proxy"),
            temperature=0.1,
        )
        #查找向量库用
        text=f"找出 {query} 的普通研判流程,⽤中⽂"
        docs = search_docs(text, knowledge_base_name, top_k, score_threshold)
        context = "\n".join([doc.page_content for doc in docs])
        #输入到大模型的最终问题
        query=(query+"\n"+"源ip服务器：[172.24.158.39:45676]"+"\n"+"访问端ip服务器：[180.215.5.133:2599]")
        #获取工具列表
        tools_list=tools[big_class]
        #代理模板
        agentpompt=Agent_PromptTemplate(
            template=agents_prompt,
            tools=tools_list,
            context=context,
            input_variables=["input", "intermediate_steps"]
        )
        #代理输出处理方式
        output_parser=Agent_OutputParser(tools=tools_list)
        print(agentpompt)
        chain = LLMChain(prompt=agentpompt, llm=model)

        agent=LLMSingleActionAgent(llm_chain=chain,
                                   output_parser=output_parser,
                                   stop=["\nObservation:"],
                                   allowed_tools=[tool.name for tool in tools_list])

        agent_executor=AgentExecutor.from_agent_and_tools(agent=agent,tools=tools_list,verbose=True)
        response = agent_executor.run(query)
        return response

    async def Organizing_info(context1,context2,model_name=model_name,temperature=temperature2,stream=False):
        callback = AsyncIteratorCallbackHandler()
        model = ChatOpenAI(
            streaming=True,
            verbose=True,
            callbacks=[callback],
            openai_api_key=llm_model_dict[model_name]["api_key"],
            openai_api_base=llm_model_dict[model_name]["api_base_url"],
            model_name=model_name,
            openai_proxy=llm_model_dict[model_name].get("openai_proxy"),
            temperature=temperature
        )

        input_msg = History(role="user", content=get_docs_prompt).to_msg_template(False)
        chat_prompt = ChatPromptTemplate.from_messages([input_msg])

        chain = LLMChain(prompt=chat_prompt, llm=model)
        task = asyncio.create_task(wrap_done(
            chain.acall({"context1": context1,"context2":context2}),
            callback.done),
        )
        if stream:
            async for token in callback.aiter():
                # Use server-sent-events to stream the response
                yield json.dumps({"answer": token},
                                 ensure_ascii=False)
        else:
            answer = ""
            async for token in callback.aiter():
                answer += token
            yield json.dumps({"answer": answer},
                             ensure_ascii=False)
            #按照日期保存到本地
            t = time.localtime()
            data = str(t.tm_mon) + "月" + str(t.tm_mday) + "日"
            data1 = str(t.tm_hour) + str(t.tm_min) + str(t.tm_sec)
            if not os.path.exists(f'./docs/{data}'):
                os.mkdir(f'./docs/{data}')
            with open(f'./docs/{data}/{data1}.txt', 'w',encoding="utf-8") as f:
                f.write(answer)

        await task

    answer_6b,bigclass=classify_model(query)
    agent_res = use_tools(answer_6b,big_class=bigclass,knowledge_base_name=knowledge_base_name)
    return StreamingResponse(Organizing_info(query,agent_res),
                             media_type="text/event-stream")



def fastapi_stream2generator(response: StreamingResponse, as_json: bool = False):
    '''
    将api.py中视图函数返回的StreamingResponse转化为同步生成器
    '''
    try:
        loop = asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()

    for chunk in iter_over_async(response.body_iterator, loop):
        if as_json and chunk:
            yield json.loads(chunk)
        elif chunk.strip():
            yield chunk


def iter_over_async(ait, loop):
    '''
    将异步生成器封装成同步生成器.
    '''
    ait = ait.__aiter__()

    async def get_next():
        try:
            obj = await ait.__anext__()
            return False, obj
        except StopAsyncIteration:
            return True, None

    while True:
        done, obj = loop.run_until_complete(get_next())
        if done:
            break
        yield obj
