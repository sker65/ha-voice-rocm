# Wyoming-Shim vor dem speech.cpp-Server: Stimmen, Stil-Tags und Tageszeit-Stil
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir wyoming==1.11.0 httpx==0.28.1 tzdata

COPY speechcpp_wrapper.py speechcpp_handler.py styles.py styles.json ./

EXPOSE 10208
ENTRYPOINT ["python3", "speechcpp_wrapper.py"]
