from dotenv import load_dotenv
from pathlib import Path

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate

# Load .env from project root (parent directory)
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Initialize the chat model
model = init_chat_model("gpt-4o-mini", model_provider="openai")

# Define the prompt template
system_template = "Translate the following from English into {language}"

# Create the prompt template
prompt_template = ChatPromptTemplate.from_messages(
    [("system", system_template), ("user", "{text}")]
)

# Invoke the prompt template
prompt = prompt_template.invoke({"language": "Portuguese", "text": "hello!"})

print(prompt)

response = model.invoke(prompt)
print(response.content)
