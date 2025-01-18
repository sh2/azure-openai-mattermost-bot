#!/bin/bash

podman run \
        --detach \
        --restart=always \
        --env=MATTERMOST_URL=http://127.0.0.1 \
        --env=MATTERMOST_PORT=8065 \
        --env=MATTERMOST_API_PATH=/api/v4 \
        --env=BOT_TOKEN= \
        --env=AZURE_OPENAI_SERVICE= \
        --env=AZURE_OPENAI_BASE_URL= \
        --env=AZURE_OPENAI_DEPLOYMENT= \
        --env=AZURE_OPENAI_API_VERSION= \
        --env=AZURE_OPENAI_API_KEY= \
        --env=AZURE_OPENAI_PROXY= \
        --env=AZURE_OPENAI_SKIP_SYSTEM_PROMPT= \
        --name=openai-chat-bot \
        openai-chat-bot:20240101
