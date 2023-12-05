import logging
import os

# 日志格式
LOG_FORMAT = "%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(format=LOG_FORMAT)

# 日志存放地址
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
if not os.path.exists(LOG_PATH):
    os.mkdir(LOG_PATH)

llm_model_dict = {
    # "chatglm2-6b": {
    #     "local_model_path": "chatglm-6b",
    #     "api_base_url": "http://localhost:8888/v1",
    #     "api_key": "EMPTY"
    # },
    "chatglm2-6b": {
        "api_base_url": "http://127.0.0.1:8888/v1",
        "api_key": os.getenv("zhupu_API_KEY"),
        "provider": "ChatGLMWorker",
        "version": "chatglm_pro"
    },

    "chatglm-130b-api": {
        "api_base_url": "http://127.0.0.1:7777/v1",
        "api_key": os.getenv("zhupu_API_KEY"),
        "provider": "ChatGLMWorker",
        "version": "chatglm_pro"
    }
}

embedding_model_dict = {
    "m3e-base": "F:\下载文件\模型\m3e-base"
}

# 设置使用的模型
LLM_MODEL_6B = "chatglm2-6b"
LLM_MODEL_130B = "chatglm-130b-api"
EMBEDDING_MODEL = "m3e-base"


#设置device，两个模型通用
LLM_DEVICE = "auto"
EMBEDDING_DEVICE = "auto"

#向量库名字
kbs_config = {
    "milvus": {
        "uri": "https://in01-397f12b4b52bc10.ali-cn-hangzhou.vectordb.zilliz.com.cn",
        "port": "19530",
        "user": "db_admin",
        "password": "password",
        "secure": False,
    }}




# 默认向量库类型
DEFAULT_VS_TYPE = "milvus"

#向量库匹配数
VECTOR_SEARCH_TOP_K=3

#匹配阈值
SCORE_THRESHOLD=1

#知识库存储地址
KB_ROOT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge")

# 知识库中单段文本长度
CHUNK_SIZE = 300

# 知识库中相邻文本重合长度
OVERLAP_SIZE = 50

#向量库默认存储路径
DB_ROOT_PATH = os.path.join(KB_ROOT_PATH, "info.db")
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_ROOT_PATH}"







