#!/bin/bash

YYYYMMDD=$(date +%Y%m%d)

podman build --tag=openai-chat-bot:${YYYYMMDD} .
