from fastapi import File, Form, Body, Query, UploadFile
from configs import VECTOR_SEARCH_TOP_K,SCORE_THRESHOLD
from typing import List
from langchain.docstore.document import Document
from server.knowledge_base.kb_service.base import KBServiceFactory

class DocumentWithScore(Document):
    score: float = None

def search_docs(query: str = Body(..., description="用户输入", examples=["你好"]),
                knowledge_base_name: str = Body(..., description="知识库名称", examples=["samples"]),
                top_k: int = Body(VECTOR_SEARCH_TOP_K, description="匹配向量数"),
                score_threshold: float = Body(SCORE_THRESHOLD, description="知识库匹配相关度阈值，取值范围在0-1之间", ge=0, le=1),
                ) -> List[DocumentWithScore]:
    """
    实现向量库查找匹配的数据并返回
    """
    kb = KBServiceFactory.get_service_by_name(knowledge_base_name)
    if kb is None:
        return []
    docs = kb.search_docs(query, top_k, score_threshold)
    data = [DocumentWithScore(**x[0].dict(), score=x[1]) for x in docs]

    return data