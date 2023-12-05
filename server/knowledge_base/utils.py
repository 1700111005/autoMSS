import os
from configs import KB_ROOT_PATH,embedding_model_dict,CHUNK_SIZE,OVERLAP_SIZE
from functools import lru_cache
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
import importlib
from text_splitter import zh_title_enhance



LOADER_DICT = {"UnstructuredHTMLLoader": ['.html'],
               "UnstructuredMarkdownLoader": ['.md'],
               "CustomJSONLoader": [".json"],
               "CSVLoader": [".csv"],
               "RapidOCRPDFLoader": [".pdf"],
               "RapidOCRLoader": ['.png', '.jpg', '.jpeg', '.bmp'],
               "UnstructuredFileLoader": ['.eml', '.msg', '.rst',
                                          '.rtf', '.txt', '.xml',
                                          '.docx', '.epub', '.odt',
                                          '.ppt', '.pptx', '.tsv'],
               }
SUPPORTED_EXTS = [ext for sublist in LOADER_DICT.values() for ext in sublist]

def get_file_path(knowledge_base_name: str, doc_name: str):
    return os.path.join(get_doc_path(knowledge_base_name), doc_name)

def get_LoaderClass(file_extension):
    for LoaderClass, extensions in LOADER_DICT.items():
        if file_extension in extensions:
            return LoaderClass

#中文标题加强
ZH_TITLE_ENHANCE = False
#把文件读取对象
class KnowledgeFile:
    def __init__(
            self,
            filename: str,
            knowledge_base_name: str
    ):
        self.kb_name = knowledge_base_name
        self.filename = filename
        self.ext = os.path.splitext(filename)[-1].lower()
        if self.ext not in SUPPORTED_EXTS:
            raise ValueError(f"暂未支持的文件格式 {self.ext}")
        self.filepath = get_file_path(knowledge_base_name, filename)
        self.docs = None
        self.document_loader_name = get_LoaderClass(self.ext)

        # TODO: 增加依据文件格式匹配text_splitter
        self.text_splitter_name = None

    def file2text(self, using_zh_title_enhance=ZH_TITLE_ENHANCE, refresh: bool = False):
        if self.docs is not None and not refresh:
            return self.docs

        print(f"{self.document_loader_name} used for {self.filepath}")
        try:
            if self.document_loader_name in ["RapidOCRPDFLoader", "RapidOCRLoader"]:
                document_loaders_module = importlib.import_module('document_loaders')
            else:
                document_loaders_module = importlib.import_module('langchain.document_loaders')
            DocumentLoader = getattr(document_loaders_module, self.document_loader_name)
        except Exception as e:
            print(e)
            document_loaders_module = importlib.import_module('langchain.document_loaders')
            DocumentLoader = getattr(document_loaders_module, "UnstructuredFileLoader")
        if self.document_loader_name == "UnstructuredFileLoader":
            loader = DocumentLoader(self.filepath, autodetect_encoding=True)
        elif self.document_loader_name == "CSVLoader":
            loader = DocumentLoader(self.filepath, encoding="utf-8")
        elif self.document_loader_name == "JSONLoader":
            loader = DocumentLoader(self.filepath, jq_schema=".", text_content=False)
        elif self.document_loader_name == "CustomJSONLoader":
            loader = DocumentLoader(self.filepath, text_content=False)
        elif self.document_loader_name == "UnstructuredMarkdownLoader":
            loader = DocumentLoader(self.filepath, mode="elements")
        elif self.document_loader_name == "UnstructuredHTMLLoader":
            loader = DocumentLoader(self.filepath, mode="elements")
        else:
            loader = DocumentLoader(self.filepath)

        if self.ext in ".csv":
            docs = loader.load()
        else:
            try:
                if self.text_splitter_name is None:
                    text_splitter_module = importlib.import_module('langchain.text_splitter')
                    TextSplitter = getattr(text_splitter_module, "SpacyTextSplitter")
                    text_splitter = TextSplitter(
                        pipeline="zh_core_web_sm",
                        chunk_size=CHUNK_SIZE,
                        chunk_overlap=OVERLAP_SIZE,
                    )
                    self.text_splitter_name = "SpacyTextSplitter"
                else:
                    text_splitter_module = importlib.import_module('langchain.text_splitter')
                    TextSplitter = getattr(text_splitter_module, self.text_splitter_name)
                    text_splitter = TextSplitter(
                        chunk_size=CHUNK_SIZE,
                        chunk_overlap=OVERLAP_SIZE)
            except Exception as e:
                print(e)
                text_splitter_module = importlib.import_module('langchain.text_splitter')
                TextSplitter = getattr(text_splitter_module, "RecursiveCharacterTextSplitter")
                text_splitter = TextSplitter(
                    chunk_size=CHUNK_SIZE,
                    chunk_overlap=OVERLAP_SIZE,
                )

            docs = loader.load_and_split(text_splitter)
        print(docs[0])
        if using_zh_title_enhance:
            docs = zh_title_enhance(docs)
        self.docs = docs
        return docs

    def get_mtime(self):
        return os.path.getmtime(self.filepath)

    def get_size(self):
        return os.path.getsize(self.filepath)


def get_kb_path(knowledge_base_name: str):
    return os.path.join(KB_ROOT_PATH, knowledge_base_name)


def get_doc_path(knowledge_base_name: str):
    return os.path.join(get_kb_path(knowledge_base_name), "content")



@lru_cache(1)
def load_embedding(model: str, device: str):
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model_dict[model], model_kwargs={'device': device})
    return embeddings