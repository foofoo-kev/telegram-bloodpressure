FROM python:3.13-alpine3.20

COPY main.py requirements.txt /

RUN pip install -r requirements.txt

CMD ["python3", "main.py"]