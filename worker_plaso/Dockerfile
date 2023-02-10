FROM log2timeline/plaso:20221229
#FROM python:3.8.10-slim-buster

RUN apt-get update && apt-get install -y \
    python3-magic \
    python3-pip \
    wget \
    p7zip-full \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN wget https://dot.net/v1/dotnet-install.sh && \
    chmod +x dotnet-install.sh && \
    ./dotnet-install.sh --version latest

RUN wget https://f001.backblazeb2.com/file/EricZimmermanTools/net6/EvtxECmd.zip \
    && 7z x EvtxECmd.zip -o.

COPY worker_plaso/requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY worker_plaso/ ./

ENTRYPOINT /usr/bin/python3 worker.py $worker_num_env