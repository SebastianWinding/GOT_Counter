import os
import socket
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import webview as pywebview
import threading

from .interface import API

js_api = API()

def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]

def start(client: str | None = None, debug: bool = False):
    if client is None:
        client = "client/"

    if os.path.exists(client):
        app = FastAPI()
        if os.path.isdir(client):
            mount_path = "/"
            serve_path = client
        else:
            mount_path = "/"
            serve_path = os.path.dirname(client)
        app.mount(mount_path, StaticFiles(directory=serve_path), name="static")

        port = get_free_port()

        def run_server(port: int):
            import uvicorn
            uvicorn.run(app, host="127.0.0.1", port=port)

        thread = threading.Thread(target=run_server, args=(port,), daemon=True)
        thread.start()
        print(f"Serving {serve_path} at http://127.0.0.1:{port}/")
        pywebview.create_window("Local Server", f"http://127.0.0.1:{port}/", js_api=js_api)
        pywebview.start(debug=debug)
    else:
        pywebview.create_window("Remote URL", client, js_api=js_api)
        pywebview.start(debug=debug)
