from server.utils import FastAPI,MakeFastAPIOffline,BaseResponse
from configs import VERSION,OPEN_CROSS_DOMAIN
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
import argparse
from server.chat.knowledge_base_chat import knowledge_base_chat
from server.chat.tools_chat import tools_chat
from server.chat.loophole import vulnerability_analysis
import uvicorn
from server.utils import ListResponse
from server.knowledge_base.kb_api import list_kbs

async def document():
    return RedirectResponse(url="/docs")

def create_app():
    app = FastAPI(
        title="chat API Server",
        version=VERSION
    )
    # MakeFastAPIOffline(app)

    if OPEN_CROSS_DOMAIN:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.get("/",
            response_model=BaseResponse,
            summary="swagger")(document)

    app.post("/chat/knowledge_base_chat",
             tags=["Chat"],
             summary="知识库对话")(knowledge_base_chat)

    # app.get("/knowledge_base/list_knowledge_bases",
    #         tags=["Knowledge Base Management"],
    #         response_model=ListResponse,
    #         summary="获取知识库列表")(list_kbs)

    app.post("/chat/tools",
             tags=["use tools"],
             summary="根据问题使用工具")(tools_chat)

    app.post("/chat/analysis",
             tags=["vulnerability analysis"],
             summary="漏洞分析")(vulnerability_analysis)


    return app

app = create_app()


def run_api(host, port, **kwargs):
    if kwargs.get("ssl_keyfile") and kwargs.get("ssl_certfile"):
        uvicorn.run(app,
                    host=host,
                    port=port,
                    ssl_keyfile=kwargs.get("ssl_keyfile"),
                    ssl_certfile=kwargs.get("ssl_certfile"),
                    )
    else:
        uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='langchain-ChatGLM')
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7861)
    parser.add_argument("--ssl_keyfile", type=str)
    parser.add_argument("--ssl_certfile", type=str)
    # 初始化消息
    args = parser.parse_args()
    args_dict = vars(args)
    run_api(host=args.host,
            port=args.port,
            ssl_keyfile=args.ssl_keyfile,
            ssl_certfile=args.ssl_certfile,
            )