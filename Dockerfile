FROM python:3.10-alpine
ENV PYTHONUNBUFFERED=1
WORKDIR /usr/src/app
COPY openai_bot.py requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt
CMD ["python", "openai_bot.py"]
