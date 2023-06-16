#FROM python:3.8.10-slim-buster
FROM python:3.10-slim-buster

#RUN apt-get update && apt-get install -y \
#    python3-magic \
#    p7zip-full \
#    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY worker_uploaders/requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt

COPY worker_uploaders/ ./

ENTRYPOINT python3 worker.py $worker_num_env