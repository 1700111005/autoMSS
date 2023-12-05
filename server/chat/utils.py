from pydantic import BaseModel, Field
from langchain.prompts.chat import ChatMessagePromptTemplate
from typing import Awaitable, List, Tuple, Dict, Union
import asyncio
from langchain.agents.tools import Tool
from langchain.prompts.base import StringPromptTemplate
from langchain.agents.agent import AgentOutputParser,AgentFinish,AgentAction
import re

class History(BaseModel):
    role: str = Field(...)
    content: str = Field(...)
    #把输入的h风格开来转变格式为，返回格式为 ai/human，问答
    def to_msg_tuple(self):
        return "ai" if self.role=="assistant" else "human", self.content

    def to_msg_template(self, is_raw=True) -> ChatMessagePromptTemplate:
        role_maps = {
            "ai": "assistant",
            "human": "user",
        }
        role = role_maps.get(self.role, self.role)
        if is_raw: # 当前默认历史消息都是没有input_variable的文本。
            content = "{% raw %}" + self.content + "{% endraw %}"
        else:
            content = self.content
        #返回langchain库的prompttemplate函数，设置模板格式为jinjia2
        return ChatMessagePromptTemplate.from_template(
            content,
            "jinja2",
            role=role,
        )
    #初始化
    @classmethod
    def from_data(cls, h: Union[List, Tuple, Dict]) -> "History":
        if isinstance(h, (list, tuple)) and len(h) >= 2:
            h = cls(role=h[0], content=h[1])
        elif isinstance(h, dict):
            h = cls(**h)
        return h

async def wrap_done(fn: Awaitable, event: asyncio.Event):
    """Wrap an awaitable with a event to signal when it's done or an exception is raised."""
    try:
        await fn
    except Exception as e:
        # TODO: handle exception
        print(f"Caught exception: {e}")
    finally:
        # Signal the aiter to stop.
        event.set()


class Agent_PromptTemplate(StringPromptTemplate):
    """
    创建自定义prompt部分，把已知信息和工具名写入自定义prompt中
    """
    template: str
    tools: List[Tool]
    context:str

    def format(self, **kwargs) -> str:
        """
        自定义prompt部分，后续可以添加向量库生成可以使用的tools，也可以通过使用参数设定添加的可以使用的tools工具
        Returns:填充好后的 template。
        """
        intermediate_steps = kwargs.pop("intermediate_steps")  # 取出中间步骤并进行执行
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought: "
        kwargs["agent_scratchpad"] = thoughts  # 记录下当前想法
        kwargs["tools"] = "\n".join(
            [f"{tool.name}: {tool.description}" for tool in self.tools]
        )
        kwargs["tool_names"] = ", ".join(
            [tool.name for tool in self.tools]
        )  # 添加所有的工具
        kwargs["content"]=self.context
        cur_prompt = self.template.format(**kwargs)
        print(cur_prompt)
        return cur_prompt


class Agent_OutputParser(AgentOutputParser):
    tools: List[Tool]

    def parse(self, llm_output: str) -> Union[AgentAction, AgentFinish]:
        """
        解析大模型输出的部分，可以在这里对输出进行格式化处理，如运行函数,增加评分
        """
        print(llm_output)
        process_all = re.findall("第二步.*?[：,:].*?\\n([\s\S]*?)\\n\\n第三步", llm_output)[0]
        process_tool = re.findall("第三步.*?[：,:].*?\\n([\s\S]*?)$", llm_output)[0]
        process_tool = process_tool.split("\n\n")
        #需要使用的工具
        tools_dict = {}
        #缺失的工具
        tools_not = "因为缺失工具而没法完成的步骤:"

        for item in process_tool:
            if "Action Input" in item:
                Action = re.findall("Action\s*[：,:]\s*[\u4e00-\u9fa5]*\s*([\s\S]*?)\s*\\n", item)[0]
                Action_Input = re.findall("Action Input[：,:].*?\s\[(.*?)]", item)[0]
                tools_dict[Action] = Action_Input
            else:
                Thought = re.findall("Thought\s*[：,:]\s([\s\S]*?)\\n", item)[0]
                tools_not += ("\n" + Thought)
        action_res=""
        for item in self.tools:
            if item.name in tools_dict.keys():
                print("*" * 100)
                print(f"调用工具:{item.name}")
                print("*" * 100)
                action_res+=(item(tools_dict[item.name])+"\n")

        llm_output="研判流程：\n"+process_all+"\n\n"+"研判的结果：\n"+action_res+"\n"+tools_not

        return AgentFinish(
                return_values={"output": action_res},
                log=llm_output,
            )

        # return AgentAction(tool=action, tool_input=action_input.strip(" ").strip('"'), log=llm_output)


