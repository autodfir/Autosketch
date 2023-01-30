import redis
import yaml
import subprocess

from rq import Connection, Worker

CONFIG_FILE = "/etc/autosketch/config.yaml"
#copy timesketchrc and timesketch.token from secrets to home direcotry
def copy_secrets():
    try:
        cmd = "cp /run/secrets/secret_rc /root/.timesketchrc"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = p.communicate()[0]
        cmd = "cp /run/secrets/secret_token /root/.timesketch.token"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = p.communicate()[0]
    except Exception as e:
        print(e)
        return "error"

copy_secrets()



with open(CONFIG_FILE, "r") as stream:
    try:
        conf = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
REDIS_IP = conf["REDIS_IP"]
REDIS_PORT = conf["REDIS_PORT"]
REDIS_URL = "redis://" + str(REDIS_IP) + ":" + str(REDIS_PORT) + "/0"

def run_worker():
    redis_url = REDIS_URL
    redis_connection = redis.from_url(redis_url)
    with Connection(redis_connection):
        worker = Worker("default")
        worker.work()


if __name__ == "__main__":
    run_worker()