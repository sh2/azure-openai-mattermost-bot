#!/bin/bash

# Mattermost
export MATTERMOST_URL=http://127.0.0.1
export MATTERMOST_PORT=8065
export MATTERMOST_API_PATH=/api/v4
export BOT_TOKEN=

# Azure OpenAI Service
export AZURE_OPENAI_SERVICE=
export AZURE_OPENAI_DEPLOYMENT=
export AZURE_OPENAI_API_VERSION=
export AZURE_OPENAI_API_KEY=
export AZURE_OPENAI_PROXY=

python3 openai-chat-bot.py
