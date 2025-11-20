import os
from dotenv import load_dotenv

from openai import OpenAI
from pathlib import Path



# Load .env from project root (parent directory)
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"

load_dotenv(env_path)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.embeddings.create(
    input="Hi my name is Tornike", model="text-embedding-3-small"
)

print(response)
