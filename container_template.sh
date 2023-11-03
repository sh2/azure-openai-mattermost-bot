#!/bin/bash

podman run \
        --detach \
        --restart=on-failure \
        --env=MATTERMOST_URL=http://127.0.0.1 \
        --env=MATTERMOST_PORT=8065 \
        --env=MATTERMOST_API_PATH=/api/v4 \
        --env=BOT_TOKEN= \
        --env=AZURE_OPENAI_SERVICE= \
        --env=AZURE_OPENAI_DEPLOYMENT= \
        --env=AZURE_OPENAI_API_VERSION= \
        --env=AZURE_OPENAI_API_KEY= \
        --env=AZURE_OPENAI_PROXY= \
        --name=openai-bot \
        openai-bot:latest