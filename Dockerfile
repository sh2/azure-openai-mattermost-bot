FROM python:3.10
ENV PYTHONUNBUFFERED=1
WORKDIR /usr/src/app
COPY chat_bot.py requirements.txt ./
RUN pip install --requirement requirements.txt
CMD ["python", "./chat_bot.py"]
