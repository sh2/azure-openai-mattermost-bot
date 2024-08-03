import base64
import httpx
import io
import json
import logging
import os
import signal
import sys
import tempfile
import threading
import traceback
import websocket

from mmpy_bot import (
    Bot,
    Message,
    Plugin,
    Settings,
    listen_to
)

from openai import AzureOpenAI, OpenAI
from PIL import Image

log = logging.getLogger("openai-image-bot")


def handler(signum, frame):
    print(f"Signal {signum} received.")
    sys.exit(0)


class ImageBot(Plugin):
    openai_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")

    def __init__(self):
        super().__init__()

        # Azure OpenAI Service
        http_client = None
        openai_proxy = os.environ.get("AZURE_OPENAI_PROXY", "")
        openai_service = os.environ.get("AZURE_OPENAI_SERVICE", "")

        if openai_proxy:
            http_client = httpx.Client(proxies=openai_proxy)

        if openai_service:
            # If the environment variable AZURE_OPENAI_SERVICE is defined, use Azure OpenAI.
            self.openai = AzureOpenAI(
                azure_endpoint=f"https://{openai_service}.openai.azure.com",

                # List of API Versions
                # https://learn.microsoft.com/en-US/azure/ai-services/openai/reference#chat-completions
                api_version=os.environ.get(
                    "AZURE_OPENAI_API_VERSION") or "2024-06-01",

                api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
                http_client=http_client
            )
        else:
            # If the environment variable AZURE_OPENAI_SERVICE is not defined, use OpenAI.
            self.openai = OpenAI(
                api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
                http_client=http_client
            )

        # Mattermost
        self.is_typing = True

        self.websocket_auth = {
            "seq": 1,
            "action": "authentication_challenge",
            "data": {
                "token": ""
            }
        }

        self.websocket_typing = {
            "action": "user_typing",
            "seq": 2,
            "data": {
                "channel_id": "",
                "parent_id": ""
            }
        }

    @listen_to("", needs_mention=True)
    def respond(self, message: Message):
        if self.driver is None:
            raise ValueError("self.driver is None")

        if self.settings is None:
            raise ValueError("self.setting is None")

        self.is_typing = True
        self.websocket_auth["data"]["token"] = self.settings.BOT_TOKEN
        self.websocket_typing["data"]["channel_id"] = message.channel_id

        # Use message.root_id. Note that message.parent_id is not defined.
        self.websocket_typing["data"]["parent_id"] = message.root_id

        log.info("API Request: " + message.text)

        try:
            # Start typing.
            # Connect separately as I cannot find a way to use the WebSocket connection
            # used by the bot itself.
            ws = websocket.WebSocket()
            ws.connect(self.build_websocket_url())
            ws.send(json.dumps(self.websocket_auth))
            self.send_typing(ws)

            # Call OpenAI's API.
            response = self.openai.images.generate(
                prompt=message.text,
                model=ImageBot.openai_deployment,
                response_format="b64_json",
                style="vivid"
            )

            # Save the image file in JPEG format and reply to the user.
            with tempfile.NamedTemporaryFile(mode="w+b", suffix=".jpg") as file:
                image = Image.open(io.BytesIO(
                    base64.b64decode(str(response.data[0].b64_json))))
                buffer = io.BytesIO()
                image.convert("RGB").save(buffer, format="JPEG", quality=85)
                file.write(buffer.getvalue())

                self.driver.reply_to(
                    message=message,
                    response=str(response.data[0].revised_prompt),
                    file_paths=[file.name]
                )
        except Exception:
            stacktrace = traceback.format_exc()
            log.error(f"Exception:\n{stacktrace}")
            self.driver.create_post(
                message.channel_id, f"Exception occured.\n```{stacktrace}```")
        finally:
            # Stop typing.
            self.is_typing = False

    def build_websocket_url(self) -> str:
        """
        Assemble and return WebSocket connection URL.
        """

        if self.settings is None:
            raise ValueError("self.setting is None")

        protocol = "ws://"

        if self.settings.SCHEME == "https":
            protocol = "wss://"

        return protocol + self.settings.MATTERMOST_URL + ":" + \
            str(self.settings.MATTERMOST_PORT) + \
            self.settings.MATTERMOST_API_PATH + "/websocket"

    def send_typing(self, ws: websocket.WebSocket):
        """
        Notify that the bot is typing.
        """

        ws.send(json.dumps(self.websocket_typing))
        if self.is_typing:
            threading.Timer(1.0, self.send_typing, args=[ws]).start()
        else:
            ws.close()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handler)
    bot = Bot(settings=Settings(), plugins=[ImageBot()])
    bot.run()
