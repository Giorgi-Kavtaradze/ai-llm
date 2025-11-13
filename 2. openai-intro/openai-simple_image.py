from openai import OpenAI  # must install openai package
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (parent directory)
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

client = OpenAI()

response = client.responses.create(
    model="gpt-5",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "What teams are playing in this image?",
                },
                {
                    "type": "input_image",
                    "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/3b/LeBron_James_Layup_%28Cleveland_vs_Brooklyn_2018%29.jpg"
                }
            ]
        }
    ]
)

print(response.output_text)
