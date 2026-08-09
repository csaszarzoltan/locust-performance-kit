"""Supported local workspace launcher."""
from __future__ import annotations

import argparse
import os

from locust_templates.workspace_api import create_workspace_app


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(prog="locust-workspace"); p.add_argument("--host",default="127.0.0.1"); p.add_argument("--port",type=int,default=8080); p.add_argument("--database"); p.add_argument("--storage-root"); p.add_argument("--allowed-root")
    a=p.parse_args(argv)
    if a.database: os.environ["LOCUST_WORKSPACE_DB"]=a.database
    if a.storage_root: os.environ["LOCUST_WORKSPACE_STORAGE_ROOT"]=a.storage_root
    if a.allowed_root: os.environ["LOCUST_WORKSPACE_ALLOWED_ROOT"]=a.allowed_root
    create_workspace_app().run(host=a.host,port=a.port,debug=False)
    return 0
if __name__=="__main__": raise SystemExit(main())
