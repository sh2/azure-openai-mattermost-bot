#!/bin/bash

# Mattermost
export MATTERMOST_URL=http://127.0.0.1
export MATTERMOST_PORT=8065
export MATTERMOST_API_PATH=/api/v4
export BOT_TOKEN=

# Azure OpenAI Service
export AZURE_OPENAI_SERVICE=
export AZURE_OPENAI_BASE_URL=
export AZURE_OPENAI_DEPLOYMENT=
export AZURE_OPENAI_API_VERSION=
export AZURE_OPENAI_API_KEY=
export AZURE_OPENAI_PROXY=
export AZURE_OPENAI_SKIP_SYSTEM_PROMPT=

python3 openai-chat-bot.py
