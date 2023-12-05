from typing import List, Dict, Optional

from langchain.embeddings.base import Embeddings
from langchain.schema import Document
from langchain.vectorstores import Milvus,Zilliz

from configs.model_config import kbs_config

from server.knowledge_base.kb_service.base import KBService, SupportedVSType, EmbeddingsFunAdapter, \
    score_threshold_process
from server.knowledge_base.utils import KnowledgeFile


class MilvusKBService(KBService):
    milvus: Milvus

    @staticmethod
    def get_collection(milvus_name):
        from pymilvus import Collection
        return Collection(milvus_name)

    def get_doc_by_id(self, id: str) -> Optional[Document]:
        if self.milvus.col:
            data_list = self.milvus.col.query(expr=f'pk == {id}', output_fields=["*"])
            if len(data_list) > 0:
                data = data_list[0]
                text = data.pop("text")
                return Document(page_content=text, metadata=data)

    @staticmethod
    def search(milvus_name, content, limit=3):
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10},
        }
        c = MilvusKBService.get_collection(milvus_name)
        return c.search(content, "embeddings", search_params, limit=limit, output_fields=["content"])

    def do_create_kb(self):
        pass

    def vs_type(self) -> str:
        return SupportedVSType.MILVUS

    def _load_milvus(self, embeddings: Embeddings = None):
        if embeddings is None:
            embeddings = self._load_embeddings()
        # self.milvus = Milvus(embedding_function=EmbeddingsFunAdapter(embeddings),
        #                      collection_name=self.kb_name, connection_args=kbs_config.get("milvus"))
        self.milvus=Zilliz(embedding_function=EmbeddingsFunAdapter(embeddings), collection_name=self.kb_name, connection_args=kbs_config.get("milvus"))

    def do_init(self):
        self._load_milvus()

    def do_drop_kb(self):
        if self.milvus.col:
            self.milvus.col.drop()

    def do_search(self, query: str, top_k: int, score_threshold: float, embeddings: Embeddings):
        self._load_milvus(embeddings=EmbeddingsFunAdapter(embeddings))
        return score_threshold_process(score_threshold, top_k, self.milvus.similarity_search_with_score(query, top_k))

    def do_add_doc(self, docs: List[Document], **kwargs) -> List[Dict]:
        ids = self.milvus.add_documents(docs)
        doc_infos = [{"id": id, "metadata": doc.metadata} for id, doc in zip(ids, docs)]
        return doc_infos

    def do_delete_doc(self, kb_file: KnowledgeFile, **kwargs):
        if self.milvus.col:
            filepath = kb_file.filepath.replace('\\', '\\\\')
            delete_list = [item.get("pk") for item in
                           self.milvus.col.query(expr=f'source == "{filepath}"', output_fields=["pk"])]
            self.milvus.col.delete(expr=f'pk in {delete_list}')

    def do_clear_vs(self):
        if self.milvus.col:
            self.milvus.col.drop()


if __name__ == '__main__':
    import glob
    # 尝试建表
    from server.datebase.base import Base, engine
    fir_list=glob.glob("../knowledge/mss/*")
    Base.metadata.create_all(bind=engine)
    milvusService = MilvusKBService("mss")
    for item in fir_list:
        milvusService.add_doc(KnowledgeFile(item.split("\\")[-1], "mss"))


