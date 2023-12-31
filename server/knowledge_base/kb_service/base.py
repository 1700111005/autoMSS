from configs import EMBEDDING_MODEL,kbs_config,VECTOR_SEARCH_TOP_K,SCORE_THRESHOLD
from typing import List, Union, Dict, Optional
from abc import ABC, abstractmethod
from server.knowledge_base.utils import get_kb_path,get_doc_path,load_embedding,KnowledgeFile
from server.utils import embedding_device
from langchain.embeddings.base import Embeddings
from langchain.docstore.document import Document
import os
from server.datebase.knowledge import (add_kb_to_db,add_file_to_db,delete_file_from_db,file_exists_in_db,list_files_from_db,
                                       delete_files_from_db,delete_kb_from_db,count_files_from_db,list_kbs_from_db,list_docs_from_db,
                                       kb_exists,load_kb_from_db)
from sklearn.preprocessing import normalize
import operator
import numpy as np

class SupportedVSType:
    FAISS = 'faiss'
    MILVUS = 'milvus'
    DEFAULT = 'default'
    PG = 'pg'

class KBService(ABC):

    def __init__(self,
                 knowledge_base_name: str,
                 embed_model: str = EMBEDDING_MODEL,
                 ):
        self.kb_name = knowledge_base_name
        self.embed_model = EMBEDDING_MODEL
        self.kb_path = get_kb_path(self.kb_name)
        self.doc_path = get_doc_path(self.kb_name)
        self.do_init()

    def _load_embeddings(self, embed_device: str = embedding_device()) -> Embeddings:
        return load_embedding(self.embed_model, embed_device)

    def create_kb(self):
        """
        创建知识库
        """
        if not os.path.exists(self.doc_path):
            os.makedirs(self.doc_path)
        self.do_create_kb()
        status = add_kb_to_db(self.kb_name, self.vs_type(), self.embed_model)
        return status

    def clear_vs(self):
        """
        删除向量库中所有内容
        """
        self.do_clear_vs()
        status = delete_files_from_db(self.kb_name)
        return status

    def drop_kb(self):
        """
        删除知识库
        """
        self.do_drop_kb()
        status = delete_kb_from_db(self.kb_name)
        return status

    def delete_doc(self, kb_file: KnowledgeFile, delete_content: bool = False, **kwargs):
        """
        从知识库删除文件
        """
        self.do_delete_doc(kb_file, **kwargs)
        status = delete_file_from_db(kb_file)
        if delete_content and os.path.exists(kb_file.filepath):
            os.remove(kb_file.filepath)
        return status

    def add_doc(self, kb_file: KnowledgeFile, docs: List[Document] = [], **kwargs):
        """
        向知识库添加文件
        如果指定了docs，则不再将文本向量化，并将数据库对应条目标为custom_docs=True
        """
        if docs:
            custom_docs = True
        else:
            docs = kb_file.file2text()
            custom_docs = False

        if docs:
            self.delete_doc(kb_file)
            doc_infos = self.do_add_doc(docs, **kwargs)
            status = add_file_to_db(kb_file,
                                    custom_docs=custom_docs,
                                    docs_count=len(docs),
                                    doc_infos=doc_infos)
        else:
            status = False
        return status

    def update_doc(self, kb_file: KnowledgeFile, docs: List[Document] = [], **kwargs):
        """
        使用content中的文件更新向量库
        如果指定了docs，则使用自定义docs，并将数据库对应条目标为custom_docs=True
        """
        if os.path.exists(kb_file.filepath):
            self.delete_doc(kb_file, **kwargs)
            return self.add_doc(kb_file, docs=docs, **kwargs)

    def exist_doc(self, file_name: str):
        return file_exists_in_db(KnowledgeFile(knowledge_base_name=self.kb_name,
                                        filename=file_name))

    def list_files(self):
        return list_files_from_db(self.kb_name)

    def count_files(self):
        return count_files_from_db(self.kb_name)

    def search_docs(self,
                    query: str,
                    top_k: int = VECTOR_SEARCH_TOP_K,
                    score_threshold: float = SCORE_THRESHOLD,
                    ):
        embeddings = self._load_embeddings()
        docs = self.do_search(query, top_k, score_threshold, embeddings)
        return docs

    # TODO: milvus/pg需要实现该方法
    def get_doc_by_id(self, id: str) -> Optional[Document]:
        return None

    def list_docs(self, file_name: str = None, metadata: Dict = {}) -> List[Document]:
        '''
        通过file_name或metadata检索Document
        '''
        doc_infos = list_docs_from_db(kb_name=self.kb_name, file_name=file_name, metadata=metadata)
        docs = [self.get_doc_by_id(x["id"]) for x in doc_infos]
        return docs

    @abstractmethod
    def do_create_kb(self):
        """
        创建知识库子类实自己逻辑
        """
        pass

    @staticmethod
    def list_kbs_type():
        return list(kbs_config.keys())

    @classmethod
    def list_kbs(cls):
        return list_kbs_from_db()

    def exists(self, kb_name: str = None):
        kb_name = kb_name or self.kb_name
        return kb_exists(kb_name)

    @abstractmethod
    def vs_type(self) -> str:
        pass

    @abstractmethod
    def do_init(self):
        pass

    @abstractmethod
    def do_drop_kb(self):
        """
        删除知识库子类实自己逻辑
        """
        pass

    @abstractmethod
    def do_search(self,
                  query: str,
                  top_k: int,
                  score_threshold: float,
                  embeddings: Embeddings,
                  ) -> List[Document]:
        """
        搜索知识库子类实自己逻辑
        """
        pass

    @abstractmethod
    def do_add_doc(self,
                   docs: List[Document],
                   ) -> List[Dict]:
        """
        向知识库添加文档子类实自己逻辑
        """
        pass

    @abstractmethod
    def do_delete_doc(self,
                      kb_file: KnowledgeFile):
        """
        从知识库删除文档子类实自己逻辑
        """
        pass

    @abstractmethod
    def do_clear_vs(self):
        """
        从知识库删除全部向量子类实自己逻辑
        """
        pass



class KBServiceFactory:
    @staticmethod
    def get_service(kb_name: str,
                    vector_store_type: Union[str, SupportedVSType],
                    embed_model: str = EMBEDDING_MODEL,
                    ) -> KBService:
        if isinstance(vector_store_type, str):
            vector_store_type = getattr(SupportedVSType, vector_store_type.upper())
        if SupportedVSType.FAISS == vector_store_type:
            from server.milvus_kb_service import MilvusKBService
            return MilvusKBService(kb_name,
                                   embed_model=embed_model)  # other milvus parameters are set in model_config.kbs_config


    @staticmethod
    def get_service_by_name(kb_name: str
                            ) -> KBService:
        _, vs_type, embed_model = load_kb_from_db(kb_name)
        if vs_type is None and os.path.isdir(get_kb_path(kb_name)):  # faiss knowledge base not in db
            vs_type = "faiss"
        return KBServiceFactory.get_service(kb_name, vs_type, embed_model)


class EmbeddingsFunAdapter(Embeddings):

    def __init__(self, embeddings: Embeddings):
        self.embeddings = embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return normalize(self.embeddings.embed_documents(texts))

    def embed_query(self, text: str) -> List[float]:
        query_embed = self.embeddings.embed_query(text)
        query_embed_2d = np.reshape(query_embed, (1, -1))  # 将一维数组转换为二维数组
        normalized_query_embed = normalize(query_embed_2d)
        return normalized_query_embed[0].tolist()  # 将结果转换为一维数组并返回

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return await normalize(self.embeddings.aembed_documents(texts))

    async def aembed_query(self, text: str) -> List[float]:
        return await normalize(self.embeddings.aembed_query(text))

def score_threshold_process(score_threshold, k, docs):
    if score_threshold is not None:
        cmp = (
            operator.le
        )
        docs = [
            (doc, similarity)
            for doc, similarity in docs
            if cmp(similarity, score_threshold)
        ]
    return docs[:k]
