import zhipuai
from server.model_workers.base import ApiModelWorker
from fastchat import conversation as conv
import sys
import json
from typing import List, Literal



class ChatGLMWorker(ApiModelWorker):
    BASE_URL = "https://open.bigmodel.cn/api/paas/v3/model-api"
    SUPPORT_MODELS = ["chatglm_pro", "chatglm_std", "chatglm_lite"]

    def __init__(
            self,
            *,
            model_names: List[str] = ["chatglm-api"],
            version: Literal["chatglm_pro", "chatglm_std", "chatglm_lite"] = "chatglm_pro",
            controller_addr: str,
            worker_addr: str,
            **kwargs,
    ):
        kwargs.update(model_names=model_names, controller_addr=controller_addr, worker_addr=worker_addr)
        kwargs.setdefault("context_len", 32768)
        super().__init__(**kwargs)
        self.version = "chatglm_pro"

        # prompt模板
        self.conv = conv.Conversation(
            name="chatglm-api",
            system_message="你是一个安全专家，你可以在指令的要求内对安全问题提供帮助",
            messages=[],
            roles=["Human", "Assistant"],
            sep="\n### ",
            stop_str="###",
        )

    def generate_stream_gate(self, params):
        # TODO: 支持stream参数，维护request_id，传过来的prompt也有问题
        from server.utils import get_model_worker_config

        super().generate_stream_gate(params)

        zhipuai.api_key = get_model_worker_config("chatglm-130b-api").get("api_key")
        response = zhipuai.model_api.sse_invoke(
            model=self.version,
            prompt=[{"role": "user", "content": params["prompt"]}],
            temperature=params.get("temperature"),
            top_p=params.get("top_p"),
            incremental=False,
        )

        for e in response.events():
            if e.event == "add":
                yield json.dumps({"error_code": 0, "text": e.data}, ensure_ascii=False).encode() + b"\0"
            # TODO: 更健壮的消息处理
            # elif e.event == "finish":
            #     ...

    def get_embeddings(self, params):
        # TODO: 支持embeddings
        print("embedding")
        print(params)


if __name__ == "__main__":
    import uvicorn
    from server.utils import MakeFastAPIOffline
    from fastchat.serve.model_worker import app

    worker = ChatGLMWorker(
        controller_addr="http://127.0.0.1:20001",
        worker_addr="http://127.0.0.1:20003",
    )
    sys.modules["fastchat.serve.model_worker"].worker = worker
    MakeFastAPIOffline(app)
    uvicorn.run(app, port=20003)
