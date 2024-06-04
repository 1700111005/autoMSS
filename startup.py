import sys
import asyncio
import multiprocessing as mp
from multiprocessing import Process, Queue
import argparse
from configs import (logger, LOG_PATH,FSCHAT_CONTROLLER,FSCHAT_OPENAI_API_6B,FSCHAT_OPENAI_API_130B
                     ,LLM_MODEL_6B,LLM_MODEL_130B,API_SERVER,WEBUI_SERVER)
from server.utils import (FastAPI,MakeFastAPIOffline,set_httpx_timeout,fschat_controller_address,
                          get_model_worker_config,fschat_model_worker_address)
from typing import Tuple, List, Dict
import subprocess



# 命令行参数设置用
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a",
        "--all-model",
        action="store_true",
        help="运行所有模型",
        dest="all_model",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="减少fastchat服务log信息",
        dest="quiet",
    )
    parser.add_argument(
        "-c",
        "--controller",
        type=str,
        help="specify controller address the worker is registered to. default is server_config.FSCHAT_CONTROLLER",
        dest="controller_address")
    args = parser.parse_args()
    args.model_name_6b=LLM_MODEL_6B
    args.model_name_130b = LLM_MODEL_130B
    return args, parser

def create_controller_app(
        dispatch_method: str,
        log_level: str = "INFO",
) -> FastAPI:
    import fastchat.constants
    fastchat.constants.LOGDIR = LOG_PATH
    from fastchat.serve.controller import app, Controller, logger

    logger.setLevel(log_level)
    controller = Controller(dispatch_method)
    sys.modules["fastchat.serve.controller"].controller = controller

    MakeFastAPIOffline(app)
    app.title = "FastChat Controller"
    app._controller = controller
    return app


def run_controller(q: Queue, run_seq: int = 1, log_level: str = "INFO", e: mp.Event = None):
    import uvicorn

    app = create_controller_app(
        dispatch_method=FSCHAT_CONTROLLER.get("dispatch_method"),
        log_level=log_level,
    )
    #
    _set_app_seq(app, q, run_seq)

    #同步多线程
    @app.on_event("startup")
    def on_startup():
        if e is not None:
            e.set()

    host = FSCHAT_CONTROLLER["host"]
    port = FSCHAT_CONTROLLER["port"]

    if log_level == "ERROR":
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    uvicorn.run(app, host=host, port=port, log_level=log_level.lower())


def run_openai_6b_api(q: Queue, run_seq: int = 3, log_level: str = "INFO"):
    '''
    生成6b的openai部分
    :param q: 多线程列表
    :param run_seq: 多线程序号
    :param log_level: 日记等级
    :return:
    '''
    import uvicorn
    controller_addr = fschat_controller_address()
    app = create_openai_api_app(controller_addr, log_level=log_level,model_name="6b")
    _set_app_seq(app, q, run_seq)

    if log_level == "ERROR":
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    host = FSCHAT_OPENAI_API_6B["host"]
    port = FSCHAT_OPENAI_API_6B["port"]
    uvicorn.run(app, host=host, port=port)

def run_openai_130b_api(q: Queue, run_seq: int = 3, log_level: str = "INFO"):
    '''
    生成130b的openai部分
    :param q: 多线程列表
    :param run_seq: 多线程序号
    :param log_level: 日记等级
    :return:
    '''
    import uvicorn
    controller_addr = fschat_controller_address()
    app = create_openai_api_app(controller_addr, log_level=log_level,model_name="130b")
    _set_app_seq(app, q, run_seq)

    if log_level == "ERROR":
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    host = FSCHAT_OPENAI_API_130B["host"]
    port = FSCHAT_OPENAI_API_130B["port"]
    uvicorn.run(app, host=host, port=port)

def create_openai_api_app(
        controller_address: str,
        api_keys: List = [],
        log_level: str = "INFO",
        model_name:str = "6b"
) -> FastAPI:
    '''
    生成openai api用
    :return:
    '''
    import fastchat.constants
    fastchat.constants.LOGDIR = LOG_PATH
    from fastchat.serve.openai_api_server import app, CORSMiddleware, app_settings
    from fastchat.utils import build_logger

    logger = build_logger(f"openai_{model_name}_api", f"openai_{model_name}_api.log")
    logger.setLevel(log_level)

    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # sys.modules["fastchat.serve.openai_api_server"].logger = logger

    app_settings.controller_address = controller_address
    app_settings.api_keys = api_keys

    MakeFastAPIOffline(app)
    app.title = f"FastChat OpeanAI API {model_name} Server"
    return app

def run_model_worker(
        model_name: str,
        controller_address: str = "",
        q: Queue = None,
        run_seq: int = 2,
        log_level: str = "INFO",
):
    '''
    设置模型相关配置，并设置模型运行对象
    '''
    import uvicorn
    kwargs = get_model_worker_config(model_name)
    host = kwargs.pop("host")
    port = kwargs.pop("port")
    # print(port)
    # print("*"*100)
    kwargs["model_names"] = [model_name]
    kwargs["controller_address"] = controller_address or fschat_controller_address()
    kwargs["worker_address"] = fschat_model_worker_address(model_name)
    #模型存放地址
    model_path = kwargs.get("local_model_path", "")
    kwargs["model_path"] = model_path
    '''print(kwargs)
    {'device': 'cpu', 'api_base_url': 'http://127.0.0.1:7777/v1', 
    'api_key': None, 'provider': 'ChatGLMWorker', 
    'version': 'chatglm_pro', 'online_api': True, 
    'worker_class': <class 'server.model_workers.zhipu.ChatGLMWorker'>, 
    'model_names': ['chatglm-130b-api'], 
    'controller_address': 'http://127.0.0.1:20001', 
    'worker_address': 'http://127.0.0.1:20003', 
    'model_path': ''}
    '''
    app = create_model_worker_app(log_level=log_level, **kwargs)

    _set_app_seq(app, q, run_seq)
    if log_level == "ERROR":
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    uvicorn.run(app, host=host, port=port, log_level=log_level.lower())



def create_model_worker_app(log_level: str = "INFO", **kwargs) -> FastAPI:
    import fastchat.constants
    # 设定日志地址
    fastchat.constants.LOGDIR = LOG_PATH
    from fastchat.serve.model_worker import app, GptqConfig, AWQConfig, ModelWorker, worker_id, logger
    import argparse
    import threading
    import fastchat.serve.model_worker
    logger.setLevel(log_level)

    # workaround to make program exit with Ctrl+c
    # it should be deleted after pr is merged by fastchat
    # 修改fastchat定义的初始化函数，把他修改为守护进程，跟随主进程退出
    def _new_init_heart_beat(self):
        self.register_to_controller()
        self.heart_beat_thread = threading.Thread(
            target=fastchat.serve.model_worker.heart_beat_worker, args=(self,), daemon=True,
        )
        self.heart_beat_thread.start()

    ModelWorker.init_heart_beat = _new_init_heart_beat

    parser = argparse.ArgumentParser()
    args = parser.parse_args([])
    # default args. should be deleted after pr is merged by fastchat
    args.gpus = None
    args.max_gpu_memory = "20GiB"
    args.load_8bit = False
    args.cpu_offloading = None
    args.gptq_ckpt = None
    args.gptq_wbits = 16
    args.gptq_groupsize = -1
    args.gptq_act_order = False
    args.awq_ckpt = None
    args.awq_wbits = 16
    args.awq_groupsize = -1
    args.num_gpus = 1
    args.model_names = []
    args.conv_template = None
    args.limit_worker_concurrency = 5
    args.stream_interval = 2
    args.no_register = False
    # 把参数整合起来,有相同会覆盖
    for k, v in kwargs.items():
        setattr(args, k, v)
    if worker_class := kwargs.get("worker_class"):

        worker = worker_class(model_names=args.model_names,
                              controller_addr=args.controller_address,
                              worker_addr=args.worker_address)
    # 本地模型
    else:
        # workaround to make program exit with Ctrl+c
        # it should be deleted after pr is merged by fastchat
        # 设置为守护线程
        def _new_init_heart_beat(self):
            self.register_to_controller()
            self.heart_beat_thread = threading.Thread(
                target=fastchat.serve.model_worker.heart_beat_worker, args=(self,), daemon=True,
            )
            self.heart_beat_thread.start()

        ModelWorker.init_heart_beat = _new_init_heart_beat
        #fastchat的初始化部分
        gptq_config = GptqConfig(
            ckpt=args.gptq_ckpt or args.model_path,
            wbits=args.gptq_wbits,
            groupsize=args.gptq_groupsize,
            act_order=args.gptq_act_order,
        )
        awq_config = AWQConfig(
            ckpt=args.awq_ckpt or args.model_path,
            wbits=args.awq_wbits,
            groupsize=args.awq_groupsize,
        )


        worker = ModelWorker(
            controller_addr=args.controller_address,
            worker_addr=args.worker_address,
            worker_id=worker_id,
            model_path=args.model_path,
            model_names=args.model_names,
            limit_worker_concurrency=args.limit_worker_concurrency,
            no_register=args.no_register,
            device=args.device,
            num_gpus=args.num_gpus,
            max_gpu_memory=args.max_gpu_memory,
            load_8bit=args.load_8bit,
            cpu_offloading=args.cpu_offloading,
            gptq_config=gptq_config,
            awq_config=awq_config,
            stream_interval=args.stream_interval,
            conv_template=args.conv_template,
        )
        sys.modules["fastchat.serve.model_worker"].args = args
        sys.modules["fastchat.serve.model_worker"].gptq_config = gptq_config

    sys.modules["fastchat.serve.model_worker"].worker = worker

    MakeFastAPIOffline(app)
    app.title = f"FastChat LLM Server ({args.model_names[0]})"
    app._worker = worker
    return app

def run_api_server(q: Queue, run_seq: int = 4):
    from server.api import create_app
    import uvicorn

    app = create_app()
    # 把app设置为启动时候就触发
    _set_app_seq(app, q, run_seq)

    host = API_SERVER["host"]
    port = API_SERVER["port"]

    uvicorn.run(app, host=host, port=port)


def _set_app_seq(app: FastAPI, q: Queue, run_seq: int):
    '''
    设置超时时间与线程启动顺序
    :param app:
    :param q:
    :param run_seq:
    :return:
    '''
    if q is None or not isinstance(run_seq, int):
        return
    if run_seq == 1:
        @app.on_event("startup")
        async def on_startup():
            set_httpx_timeout()
            q.put(run_seq)
    elif run_seq > 1:
        @app.on_event("startup")
        async def on_startup():
            set_httpx_timeout()
            while True:
                no = q.get()
                if no != run_seq - 1:
                    q.put(no)
                else:
                    break
            q.put(run_seq)

def run_webui(q: Queue, run_seq: int = 5):
    host = WEBUI_SERVER["host"]
    port = WEBUI_SERVER["port"]

    if q is not None and isinstance(run_seq, int):
        while True:
            no = q.get()
            if no != run_seq - 1:
                q.put(no)
            else:
                break
        q.put(run_seq)
    #127.0.0.1：8501，把webui运行到8501端口上
    p = subprocess.Popen(["streamlit", "run", "webui.py",
                          "--server.address", host,
                          "--server.port", str(port)])
    p.wait()




# 运行主体
async def run_main():
    import signal
    import time

    def handler(signalname):
        """
        Python 3.9 has `signal.strsignal(signalnum)` so this closure would not be needed.
        Also, 3.8 includes `signal.valid_signals()` that can be used to create a mapping for the same purpose.
        """

        def f(signal_received, frame):
            raise KeyboardInterrupt(f"{signalname} received")

        return f

    signal.signal(signal.SIGINT, handler("SIGINT"))
    signal.signal(signal.SIGTERM, handler("SIGTERM"))

    mp.set_start_method("spawn")
    manager = mp.Manager()

    queue = manager.Queue()
    args, parser = parse_args()
    if args.all_model:
        args.model_130b = True
        args.model_6b = True
        args.webui = True
        args.openai_api = True
        args.api = True

    # print(args.api_model)

    if len(sys.argv) > 1:
        logger.info(f"正在启动服务：")
        logger.info(f"如需查看 llm_api 日志，请前往 {LOG_PATH}")

    # 记录多线程用
    processes = {}
    controller_started = manager.Event()

    def process_count():
        return len(processes)

    if args.quiet:
        log_level = "ERROR"
    else:
        log_level = "INFO"


    # 设置线程启动部分

    if args.openai_api:
        #"127.0.0.1:20001"
        process = Process(
            target=run_controller,
            name=f"controller",
            args=(queue, process_count() + 1, log_level, controller_started),
            daemon=True,
        )
        processes["controller"] = process

        #"127.0.0.1:8888"
        process = Process(
            target=run_openai_6b_api,
            name=f"openai_6b_api",
            args=(queue, process_count() + 1),
            daemon=True,
        )
        processes["openai_6b_api"] = process
        # "127.0.0.1:7777"
        process = Process(
            target=run_openai_130b_api,
            name=f"openai_130b_api",
            args=(queue, process_count() + 1),
            daemon=True,
        )
        processes["openai_130b_api"] = process

    if args.model_130b:
        # "127.0.0.1:20003"
        process = Process(
            target=run_model_worker,
            name=f"model_worker - {args.model_name_130b}",
            args=(args.model_name_130b, args.controller_address, queue, process_count() + 1, log_level),
            daemon=True,
        )
        processes["model_130b"] = process

    if args.model_6b:
        # "127.0.0.1:20002"
        process = Process(
            target=run_model_worker,
            name=f"model_worker - {args.model_name_6b}",
            args=(args.model_name_6b, args.controller_address, queue, process_count() + 1, log_level),
            daemon=True,
        )
        processes["model_6b"] = process

    if args.api:
        # 127.0.0.1：6666
        process = Process(
            target=run_api_server,
            name=f"API Server",
            args=(queue, process_count() + 1),
            daemon=True,
        )
        processes["api"] = process

    if args.webui:
        #127.0.0.1：3333
        process = Process(
            target=run_webui,
            name=f"WEBUI Server",
            args=(queue, process_count() + 1),
            daemon=True,
        )

        processes["webui"] = process

    # if args.args.webui:
    #     raise

    if process_count() == 0:
        parser.print_help()
    else:
        try:
            if p := processes.get("controller"):
                p.start()
                p.name = f"{p.name} ({p.pid})"
                controller_started.wait()

            if p := processes.get("openai_6b_api"):
                p.start()
                p.name = f"{p.name} ({p.pid})"
                controller_started.wait()
            if p := processes.get("openai_130b_api"):
                p.start()
                p.name = f"{p.name} ({p.pid})"
                controller_started.wait()
            if p := processes.get("model_130b"):
                p.start()
                p.name = f"{p.name} ({p.pid})"
                controller_started.wait()
            if p := processes.get("model_6b"):
                p.start()
                p.name = f"{p.name} ({p.pid})"
                controller_started.wait()
            if p := processes.get("api"):
                p.start()
                p.name = f"{p.name} ({p.pid})"
                controller_started.wait()

            while True:
                no = queue.get()
                if no == process_count():
                    time.sleep(0.5)
                    # dump_server_info(after_start=True, args=args)
                    break
                else:
                    queue.put(no)

        except Exception as e:
            logger.error(e)
            logger.warning("Caught KeyboardInterrupt! Setting stop event...")

        finally:
            # Send SIGINT if process doesn't exit quickly enough, and kill it as last resort
            # .is_alive() also implicitly joins the process (good practice in linux)
            # while alive_procs := [p for p in processes.values() if p.is_alive()]:

            for p in processes.values():
                logger.warning("Sending SIGKILL to %s", p)
                # Queues and other inter-process communication primitives can break when
                # process is killed, but we don't care here

                if isinstance(p, list):
                    for process in p:
                        process.kill()

                else:
                    p.kill()

            for p in processes.values():
                logger.info("Process status: %s", p)



if __name__ == "__main__":

    if sys.version_info < (3, 10):
        loop = asyncio.get_event_loop()
    else:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)
    # 同步调用协程代码
    loop.run_until_complete(run_main())
