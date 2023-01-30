
FROM python:3.10-slim-buster

WORKDIR /app

ARG flask_var=web.py
ENV FLASK_APP=$flask_var

COPY web/requirements.txt /app/requirements.txt

RUN pip3 install -r requirements.txt

COPY web /app


RUN ["flask", "--app","web","init-db"]

CMD [ "python3" , "web.py"]
