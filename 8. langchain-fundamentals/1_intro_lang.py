# import getpass
# import os
from langchain_core.messages import HumanMessage, SystemMessage

from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root (parent directory)
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Load environment variables
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-4o-mini", model_provider="openai")

messages = [
    SystemMessage("Translate the following from English into Italian"),
    HumanMessage("hi!"),
]


print(messages)

response = model.invoke(messages)

print(response)
