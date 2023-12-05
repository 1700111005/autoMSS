from fastapi import Body, Request
from configs import VECTOR_SEARCH_TOP_K, SCORE_THRESHOLD, LLM_MODEL_130B, llm_model_dict
from typing import AsyncIterable, List, Optional

from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.chat_models import ChatOpenAI
from server.chat.utils import History, wrap_done
import asyncio
import json
from fastapi.responses import StreamingResponse
from langchain.agents import AgentType
from langchain.agents import load_tools, initialize_agent, tool
import sys


def tools_chat(query: str = Body(..., description="用户输入"),
               stream: bool = Body(False, description="流式输出"),
               model_name: str = Body(LLM_MODEL_130B, description="LLM 模型名称。"),
               temperature: int = Body(0, description="模型温度", ge=0, le=1),
               ):
    async def use_tools(query: str, model_name: str = model_name) -> AsyncIterable[str]:
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

        tools = make_tool_list(model)

        agent = initialize_agent(
            tools,
            model,
            agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,  # 代理类型
            handle_parsing_errors=True,
            verbose=True,  # 输出中间步骤
        )

        task = asyncio.create_task(wrap_done(
            agent.acall({'input': query}),
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

        await task

    return StreamingResponse(use_tools(query, model_name),
                             media_type="text/event-stream")
