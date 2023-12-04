import httpx
import json
import logging
import os
import re
import threading
import time
import traceback
import websocket

from mmpy_bot import (
    Bot,
    Message,
    Plugin,
    Settings,
    listen_to
)

from openai import AzureOpenAI

log = logging.getLogger("openai_bot")


class OpenAIBot(Plugin):
    azure_openai_deployment = os.environ.get(
        "AZURE_OPENAI_DEPLOYMENT", "deploy1")

    def __init__(self):
        super().__init__()

        # Azure OpenAI Service
        openai_proxy = os.environ.get("AZURE_OPENAI_PROXY", "")
        http_client = None

        if openai_proxy:
            http_client = httpx.Client(proxies=openai_proxy)

        self.openai = AzureOpenAI(
            azure_endpoint=f"https://{os.environ.get('AZURE_OPENAI_SERVICE', 'openai1')}.openai.azure.com",

            # List of API Versions
            # https://learn.microsoft.com/en-US/azure/ai-services/openai/reference#chat-completions
            api_version=os.environ.get(
                "AZURE_OPENAI_API_VERSION", "2023-08-01-preview"),

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

    @listen_to("")
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

        # Get the entire thread.
        thread = self.driver.get_post_thread(message.id)

        # If you use needs_mention in the listen_to decorator,
        # you can only see the last remark, so don't use this,
        # but look at the whole thread to determine if you should reply to the message.
        if not self.is_reply_required(thread, message.sender_name):
            return

        # Get channel headers and use them as system prompts.
        channels = self.driver.channels  # type: ignore
        system_prompt = channels.get_channel(message.channel_id)["header"]

        # Assemble the request message.
        # TODO: Check if the number of tokens is exceeded.
        requestMessages = self.build_request_messages(
            thread, self.driver.user_id, system_prompt)
        log.info("API Request: " +
                 json.dumps(requestMessages, ensure_ascii=False))

        try:
            # Start typing.
            # Connect separately as I cannot find a way to use the WebSocket connection
            # used by the bot itself.
            ws = websocket.WebSocket()
            ws.connect(self.build_websocket_url())
            ws.send(json.dumps(self.websocket_auth))
            self.send_typing(ws)

            # Call OpenAI's API.
            completion = self.openai.chat.completions.create(
                messages=requestMessages,
                model=OpenAIBot.azure_openai_deployment,
                stream=True
            )

            # Reply with an empty message and update with stream data.
            reply = self.driver.reply_to(message, "")
            reply_id = reply["id"]
            reply_chunks = []
            last_time = time.time()

            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    reply_chunks.append(chunk.choices[0].delta.content)
                    current_time = time.time()

                    # Stores stream data for one second before outputting it.
                    if last_time + 1.0 <= current_time:
                        last_time = current_time
                        reply_message = "".join(reply_chunks)
                        reply_chunks = [reply_message]

                        self.driver.posts.update_post(  # type:ignore
                            post_id=reply_id,
                            options={
                                "id": reply_id,
                                "message": reply_message
                            }
                        )

            # Update again with the last set of data.
            reply_message = "".join(reply_chunks)
            log.info("API Response: " + reply_message)

            self.driver.posts.update_post(  # type:ignore
                post_id=reply_id,
                options={
                    "id": reply_id,
                    "message": reply_message
                }
            )
        except Exception:
            stacktrace = traceback.format_exc()
            log.error(f"Exception:\n{stacktrace}")
            self.driver.create_post(
                message.channel_id, f"Exception occured.\n```{stacktrace}```")
        finally:
            # Stop typing.
            self.is_typing = False

    def is_reply_required(self, thread, sender_name: str) -> bool:
        """
        Determine if the bot should reply to the thread.
        """

        if self.driver is None:
            raise ValueError("self.driver is None")

        # To prevent bots from talking to each other,
        # do not reply to statements by users beginning with "ai-".
        if sender_name.startswith("ai-"):
            return False

        # Reply to any mentions of the bot in the thread.
        # I couldn't find a function to extract mentions in mmmpy_bot,
        # so I decided to analyze it by myself.
        pattern = r"(^|\s)@([a-z0-9\.\-_]+)(?=$|\s)"

        for post_id in thread["order"]:
            post = thread["posts"][post_id]
            matches = re.findall(pattern, post["message"])
            usernames = [match[1] for match in matches]

            if self.driver.username in usernames:
                return True

        # If the conditions up to this point are not met, the bot will not reply.
        return False

    def build_request_messages(self, thread, bot_id, system_prompt) -> list:
        """
        Assemble and return a message list to pass to the OpenAI API
        based on the content of the thread.
        """

        requestMessages = [{"role": "system", "content": system_prompt}]

        for post_id in thread["order"]:
            post = thread["posts"][post_id]
            if post["user_id"] == bot_id:
                requestMessages.append(
                    {"role": "assistant", "content": post["message"]})
            else:
                requestMessages.append(
                    {"role": "user", "content": post["message"]})

        return requestMessages

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
    bot = Bot(settings=Settings(), plugins=[OpenAIBot()])
    bot.run()
