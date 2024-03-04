FROM ubuntu:18.04

LABEL maintainer="jtam64@my.bcit.ca"

RUN apt-get update -y && apt-get install -y python3 python3-pip

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

RUN pip3 install connexion[swagger-ui]

COPY . /app

ENTRYPOINT ["python3"]

CMD ["app.py"]