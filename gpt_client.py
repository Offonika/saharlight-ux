# gpt_client.py
import openai
import os
from config import OPENAI_API_KEY, OPENAI_ASSISTANT_ID, OPENAI_PROXY

os.environ["HTTP_PROXY"] = OPENAI_PROXY
os.environ["HTTPS_PROXY"] = OPENAI_PROXY

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def create_thread() -> str:
    thread = client.beta.threads.create()
    return thread.id

def send_message(thread_id: str, content: str = None, image_path: str = None):
    # Если передаём изображение
    if image_path:
        with open(image_path, "rb") as f:
            file = client.files.create(file=f, purpose="vision")

        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=[
                {
                    "type": "image_file",
                    "image_file": {"file_id": file.id}
                },
                {
                    "type": "text",
                    "text": content or "Что изображено на фото?"
                }
            ]
        )
    else:
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content
        )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=OPENAI_ASSISTANT_ID
    )

    return run
