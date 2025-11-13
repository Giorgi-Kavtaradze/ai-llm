from openai import OpenAI  # must install openai package
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (parent directory)
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a eastern poet."},
        {
            "role": "user",
            "content": """write me a short poem about the moon. 
               Write the poem in the style of a haiku.
               Make sure include a title for the poem.""",
        },
    ],
)

print(response.choices[0].message.content)
