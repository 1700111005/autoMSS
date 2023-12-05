from fastapi import Body, Request
from configs import VECTOR_SEARCH_TOP_K, SCORE_THRESHOLD, LLM_MODEL_130B, llm_model_dict, PROMPT
from typing import AsyncIterable, List, Optional
from server.knowledge_base.kb_service.base import KBServiceFactory
from server.knowledge_base.kb_doc_api import search_docs
from server.utils import BaseResponse
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.chat_models import ChatOpenAI
from server.chat.utils import History, wrap_done
from langchain.prompts.chat import ChatPromptTemplate
from langchain import LLMChain
import asyncio
import os
from urllib.parse import urlencode
import json
from fastapi.responses import StreamingResponse


def knowledge_base_chat(query: str = Body(..., description="用户输入"),
                        knowledge_base_name: str = Body(..., description="知识库名称"),
                        top_k: int = Body(VECTOR_SEARCH_TOP_K, description="匹配向量数"),
                        score_threshold: float = Body(SCORE_THRESHOLD,
                                                      description="知识库匹配阈值",
                                                      ge=0, le=1),
                        history: List[History] = Body([], description="历史对话"),

                        stream: bool = Body(False, description="流式输出"),
                        model_name: str = Body(LLM_MODEL_130B, description="LLM 模型名称。"),
                        local_doc_url: bool = Body(False, description="知识文件返回本地路径(true)或URL(false)"),
                        request: Request = None,
                        temperature: int = Body(0, description="模型温度", ge=0, le=1),
                        big_name: str = "⽊⻢攻击"
                        ):
    kb = KBServiceFactory.get_service_by_name(knowledge_base_name)
    if kb is None:
        return BaseResponse(code=404, msg=f"未找到知识库 {knowledge_base_name}")

    history = [History.from_data(h) for h in history]

    async def knowledge_chat(query: str, top_k: int, history: Optional[List[History]],
                             model_name: str = LLM_MODEL_130B, ) -> AsyncIterable[str]:
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
        docs = search_docs(query, knowledge_base_name, top_k, score_threshold)
        context = "\n".join([doc.page_content for doc in docs])

        input_msg = History(role="user", content=PROMPT).to_msg_template(False)
        chat_prompt = ChatPromptTemplate.from_messages(
            [i.to_msg_template() for i in history] + [input_msg])

        chain = LLMChain(prompt=chat_prompt, llm=model)

        # Begin a task that runs in the background.
        task = asyncio.create_task(wrap_done(
            chain.acall({"context": context, "question": query}),
            callback.done),
        )

        source_documents = []
        for inum, doc in enumerate(docs):
            filename = os.path.split(doc.metadata["source"])[-1]
            if local_doc_url:
                url = "file://" + doc.metadata["source"]
            else:
                parameters = urlencode({"knowledge_base_name": knowledge_base_name, "file_name": filename})
                url = f"{request.base_url}knowledge_base/download_doc?" + parameters
            text = f"""出处 [{inum + 1}] [{filename}]({url}) \n\n{doc.page_content}\n\n"""
            source_documents.append(text)

        if stream:
            async for token in callback.aiter():
                # Use server-sent-events to stream the response
                yield json.dumps({"answer": token,
                                  "docs": source_documents},
                                 ensure_ascii=False)
        else:
            answer = ""
            async for token in callback.aiter():
                answer += token
            yield json.dumps({"answer": answer,
                              "docs": source_documents},
                             ensure_ascii=False)

        await task

    return StreamingResponse(knowledge_chat(query, top_k, history, model_name),
                             media_type="text/event-stream")
