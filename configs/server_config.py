from .model_config import LLM_DEVICE

#本地绑定地址
DEFAULT_BIND_HOST = "127.0.0.1"

#api跨域
OPEN_CROSS_DOMAIN = False

#fastchat controller server
FSCHAT_CONTROLLER = {
    "host": DEFAULT_BIND_HOST,
    "port": 20001,
    "dispatch_method": "shortest_queue",
}

FSCHAT_OPENAI_API_6B= {
    "host": DEFAULT_BIND_HOST,
    "port": 8888  # model_config.llm_model_dict中模型配置的api_base_url需要与这里一致。
}

FSCHAT_OPENAI_API_130B= {
    "host": DEFAULT_BIND_HOST,
    "port": 7777  # model_config.llm_model_dict中模型配置的api_base_url需要与这里一致。
}


# httpx设置超时时间。
HTTPX_DEFAULT_TIMEOUT = 300.0


#模型server相关参数
FSCHAT_MODEL_WORKERS = {
    "chatglm2-6b": {
        "host": DEFAULT_BIND_HOST,
        "port": 20002,
        "device": LLM_DEVICE,
    },
    "chatglm-130b-api": {
        "host": DEFAULT_BIND_HOST,
        "device": LLM_DEVICE,
        "port": 20003,
    },
}

API_SERVER = {
    "host": DEFAULT_BIND_HOST,
    "port": 9999,
}

WEBUI_SERVER={
    "host": DEFAULT_BIND_HOST,
    "port": 6006,
}
