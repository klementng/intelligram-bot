FROM python:3.10
#RUN apk add openssl
RUN apt install openssl
COPY ./requirements.txt /
RUN pip install -r /requirements.txt

WORKDIR /app
COPY . .

CMD ["python3","/app/main.py"]
