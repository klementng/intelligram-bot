FROM python:3.10-alpine

RUN apk add openssl
COPY ./requirements.txt /
RUN pip install -r /requirements.txt

WORKDIR /app
COPY . .

CMD ["python3","/app/main.py"]
