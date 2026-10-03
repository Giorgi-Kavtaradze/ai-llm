from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root (parent directory)
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


# Define a prompt template
prompt = ChatPromptTemplate.from_template("tell me a joke about {topic}")

# Create a chat model
model = ChatOpenAI(model="gpt-6-luna")

# Chain the prompt, model, and output parser
chain = prompt | model | StrOutputParser()

# Run the chain
response = chain.invoke({"topic": "lions"})
print(response)
