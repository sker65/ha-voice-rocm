# Wyoming-STT-Shim vor dem speech.cpp-Server (Qwen3-ASR): sammelt das Audio
# einer Äußerung als WAV und schickt es an /v1/audio/transcriptions
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir wyoming==1.11.0 httpx==0.28.1

COPY speechcpp_asr_wrapper.py speechcpp_asr_handler.py ./

EXPOSE 10309
ENTRYPOINT ["python3", "speechcpp_asr_wrapper.py"]
