import redis
import yaml
import subprocess
import multiprocessing
import sys
import time

from rq import Connection, Worker, Queue

CONFIG_FILE = "/etc/autosketch/config.yaml"


with open(CONFIG_FILE, "r") as stream:
    try:
        conf = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

REDIS_IP = conf["REDIS_IP"]
REDIS_PORT = conf["REDIS_PORT"]
REDIS_URL = "redis://" + str(REDIS_IP) + ":" + str(REDIS_PORT) + "/0"


def run_worker(queue):
    redis_url = REDIS_URL
    redis_connection = redis.from_url(redis_url)
    with Connection(redis_connection):
        worker = Worker(queue)
        worker.work()


if __name__ == "__main__":
    worker_num = sys.argv[1]

    for i in range(int(worker_num)):
        print("Started " + str(i) + "worker")
        multiprocessing.Process(target=run_worker, args=("parsers",)).start()

    while True:
        time.sleep(10)
        
