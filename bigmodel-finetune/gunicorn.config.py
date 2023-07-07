import os
import gevent.monkey
gevent.monkey.patch_all()

import multiprocessing

CPU_COUNT = os.environ.get("CPU_COUNT")

# 先删除文件夹中的文件，再删除空文件夹
log_path = "log/"

# 删除已有的日志
for file_name in os.listdir(log_path):
    file_path=os.path.join(log_path, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)

from app.fmh import FoundationModelHandler
fmh = FoundationModelHandler()
fmh.registry()

debug = True
loglevel = 'debug'
bind = "0.0.0.0:8080"
pidfile = "log/gunicorn.pid"
backlog = 512                        #监听队列

accesslog = "log/access.log"
errorlog = "log/debug.log"
daemon = False

# 启动的进程数
timeout = 60                         #超时
worker_class = "gevent"
x_forwarded_for_header = "X-FORWARDED-FOR"

print(multiprocessing.cpu_count())
workers = int(CPU_COUNT) * 2 + 1    # 进程数
threads = 4     # 指定每个进程开启的线程数


