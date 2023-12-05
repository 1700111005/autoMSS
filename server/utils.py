from fastapi import FastAPI
from typing import Optional
from pathlib import Path
import os
from server import model_workers
from configs import LLM_DEVICE,EMBEDDING_DEVICE
from typing import Literal, Optional, Any ,List
from pydantic import BaseModel
import pydantic

def MakeFastAPIOffline(
    app: FastAPI,
    static_dir = Path(__file__).parent / "static",
    static_url = "/static-offline-docs",
    docs_url: Optional[str] = "/docs",
    redoc_url: Optional[str] = "/redoc",
) -> None:
    '''
    #修改FastAPI对象属性
    :param app: 需要修改FastAPI
    '''
    """patch the FastAPI obj that doesn't rely on CDN for the documentation page"""
    from fastapi import Request
    from fastapi.openapi.docs import (
        get_redoc_html,
        get_swagger_ui_html,
        get_swagger_ui_oauth2_redirect_html,
    )
    from fastapi.staticfiles import StaticFiles
    from starlette.responses import HTMLResponse

    openapi_url = app.openapi_url
    swagger_ui_oauth2_redirect_url = app.swagger_ui_oauth2_redirect_url

    def remove_route(url: str) -> None:
        '''
        remove original route from app
        '''
        index = None
        for i, r in enumerate(app.routes):
            if r.path.lower() == url.lower():
                index = i
                break
        if isinstance(index, int):
            app.routes.pop(i)

    # Set up static file mount
    app.mount(
        static_url,
        StaticFiles(directory=Path(static_dir).as_posix()),
        name="static-offline-docs",
    )

    if docs_url is not None:
        remove_route(docs_url)
        remove_route(swagger_ui_oauth2_redirect_url)

        # Define the doc and redoc pages, pointing at the right files
        @app.get(docs_url, include_in_schema=False)
        async def custom_swagger_ui_html(request: Request) -> HTMLResponse:
            root = request.scope.get("root_path")
            favicon = f"{root}{static_url}/favicon.png"
            return get_swagger_ui_html(
                openapi_url=f"{root}{openapi_url}",
                title=app.title + " - Swagger UI",
                oauth2_redirect_url=swagger_ui_oauth2_redirect_url,
                swagger_js_url=f"{root}{static_url}/swagger-ui-bundle.js",
                swagger_css_url=f"{root}{static_url}/swagger-ui.css",
                swagger_favicon_url=favicon,
            )

        @app.get(swagger_ui_oauth2_redirect_url, include_in_schema=False)
        async def swagger_ui_redirect() -> HTMLResponse:
            return get_swagger_ui_oauth2_redirect_html()

    if redoc_url is not None:
        remove_route(redoc_url)

        @app.get(redoc_url, include_in_schema=False)
        async def redoc_html(request: Request) -> HTMLResponse:
            root = request.scope.get("root_path")
            favicon = f"{root}{static_url}/favicon.png"

            return get_redoc_html(
                openapi_url=f"{root}{openapi_url}",
                title=app.title + " - ReDoc",
                redoc_js_url=f"{root}{static_url}/redoc.standalone.js",
                with_google_fonts=False,
                redoc_favicon_url=favicon,
            )


def set_httpx_timeout(timeout: float = None):
    '''
    设置网络超时时间用
    :param timeout:
    :return:
    '''
    import httpx
    from configs.server_config import HTTPX_DEFAULT_TIMEOUT

    timeout = timeout or HTTPX_DEFAULT_TIMEOUT
    httpx._config.DEFAULT_TIMEOUT_CONFIG.connect = timeout
    httpx._config.DEFAULT_TIMEOUT_CONFIG.read = timeout
    httpx._config.DEFAULT_TIMEOUT_CONFIG.write = timeout


def fschat_controller_address()->str:
    '''
    获取fastchat地址
    :return: str
    '''
    from configs.server_config import FSCHAT_CONTROLLER

    host=FSCHAT_CONTROLLER["host"]
    port=FSCHAT_CONTROLLER["port"]

    return f"http://{host}:{port}"


# def get_all_model_worker_config() -> dict:
#     """
#     获取所有模型的参数形成列表
#     :return:
#     """
#
#     from configs.model_config import llm_model_dict
#     from configs.server_config import FSCHAT_MODEL_WORKERS
#     result = {}
#
#     model_names = set(llm_model_dict.keys()) | set(FSCHAT_MODEL_WORKERS.keys())
#     for name in model_names:
#         result[name] = get_model_worker_config(name)
#
#     return result

def detect_device() -> Literal["cuda", "mps", "cpu"]:
    '''
    使用torch自动获取device
    :return:
    '''
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except:
        pass
    return "cpu"

def llm_device(device: str = LLM_DEVICE) -> Literal["cuda", "mps", "cpu"]:
    if device not in ["cuda", "mps", "cpu"]:
        device = detect_device()
    return device

def get_model_worker_config(model_name:str):
    """
        获取指定模型的所有参数，并配置device
        :param model_name: 模型的名字
        :return 模型参数
    """
    from configs.server_config import FSCHAT_MODEL_WORKERS
    from configs.model_config import llm_model_dict
    config = FSCHAT_MODEL_WORKERS.get(model_name, {}).copy()
    config.update(llm_model_dict.get(model_name, {}))

    if not os.path.isdir(config.get("local_model_path", "")):
        config["online_api"] = True
        if provider := config.get("provider"):
            try:
                #如果使用其他api，需要添加server里面的model_workers部分
                config["worker_class"] = getattr(model_workers, provider)
            except Exception as e:
                print(f"在线模型 ‘{model_name}’ 的provider没有正确配置")
    config["device"] = llm_device(config.get("device") or LLM_DEVICE)

    return config

def fschat_model_worker_address(model_name: str) -> str:
    """
    获取模型工作的端口
    :param model_name: 模型的名字
    :return:
    """
    if model := get_model_worker_config(model_name):
        host = model["host"]
        port = model["port"]
        return f"http://{host}:{port}"
    return ""

#访问格式
class BaseResponse(BaseModel):
    code: int = pydantic.Field(200, description="API status code")
    msg: str = pydantic.Field("success", description="API status message")
    data: Any = pydantic.Field(None, description="API data")

    class Config:
        schema_extra = {
            "example": {
                "code": 200,
                "msg": "success",
            }
        }

def api_address() -> str:
    from configs.server_config import API_SERVER
    #127.0.0.1：7861
    host = API_SERVER["host"]
    port = API_SERVER["port"]
    return f"http://{host}:{port}"


def embedding_device(device: str = EMBEDDING_DEVICE) -> Literal["cuda", "mps", "cpu"]:
    if device not in ["cuda", "mps", "cpu"]:
        device = detect_device()
    return device

class ListResponse(BaseResponse):
    data: List[str] = pydantic.Field(..., description="List of names")

    class Config:
        schema_extra = {
            "example": {
                "code": 200,
                "msg": "success",
                "data": ["doc1.docx", "doc2.pdf", "doc3.txt"],
            }
        }