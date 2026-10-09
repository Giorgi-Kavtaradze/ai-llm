# pip install youtube-transcript-api

import os
import requests
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.memory import ConversationBufferMemory
from langchain_classic.chains.summarize import load_summarize_chain
from langchain_core.documents import Document


from dotenv import load_dotenv
from pathlib import Path
# Load .env from project root (parent directory)
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


class EmbeddingModel:
    """Handles different embedding models"""

    def __init__(self, model_type="openai"):
        self.model_type = model_type
        if model_type == "openai":
            self.embedding_fn = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=os.getenv("OPENAI_API_KEY"),
            )
        elif model_type == "chroma":
            from langchain_huggingface import HuggingFaceEmbeddings

            self.embedding_fn = HuggingFaceEmbeddings()
        elif model_type == "nomic":
            from langchain_ollama import OllamaEmbeddings

            self.embedding_fn = OllamaEmbeddings(
                model="nomic-embed-text", base_url="http://localhost:11434"
            )
        else:
            raise ValueError(f"Unsupported embedding type: {model_type}")


class LLMModel:
    """Handles different LLM models"""

    def __init__(self, model_type="openai", model_name="gpt-6-luna"):
        self.model_type = model_type
        self.model_name = model_name

        if model_type == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OpenAI API key is required for OpenAI models")
            self.llm = ChatOpenAI(model_name=model_name)
        elif model_type == "ollama":
            self.llm = ChatOllama(
                model=model_name,
                temperature=0,
                format="json",
                client_kwargs={"timeout": 120},
            )
        else:
            raise ValueError(f"Unsupported LLM type: {model_type}")


class YoutubeVideoSummarizer:
    def __init__(
        self, llm_type="openai", llm_model_name="gpt-6-luna", embedding_type="openai"
    ):
        """Initialize with different LLM and embedding options"""
        # Initialize Models
        self.embedding_model = EmbeddingModel(embedding_type)
        self.llm_model = LLMModel(llm_type, llm_model_name)

        # Initialize YouTube transcript client
        self.transcript_api = YouTubeTranscriptApi()

    def get_model_info(self) -> Dict:
        """Return current model configuration"""
        return {
            "llm_type": self.llm_model.model_type,
            "llm_model": self.llm_model.model_name,
            "embedding_type": self.embedding_model.model_type,
        }

    def get_video_id(self, url: str) -> str:
        """Extract the video ID from a YouTube URL"""
        parsed = urlparse(url)
        if parsed.hostname in ("youtu.be", "www.youtu.be"):
            return parsed.path.lstrip("/")
        if parsed.path == "/watch":
            return parse_qs(parsed.query)["v"][0]
        if parsed.path.startswith(("/shorts/", "/embed/", "/live/")):
            return parsed.path.split("/")[2]
        raise ValueError(f"Could not extract video ID from URL: {url}")

    def get_video_title(self, url: str) -> str:
        """Fetch video title using YouTube's oEmbed endpoint"""
        try:
            response = requests.get(
                "https://www.youtube.com/oembed",
                params={"url": url, "format": "json"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json().get("title", "Unknown Title")
        except requests.RequestException:
            return "Unknown Title"

    def get_transcript(self, video_id: str) -> str:
        """Download the video's transcript from YouTube"""
        print("Downloading transcript...")
        transcript = self.transcript_api.fetch(video_id, languages=["en"])
        return " ".join(snippet.text for snippet in transcript)

    def create_documents(self, text: str, video_title: str) -> List[Document]:
        """Split text into chunks and create Document objects"""
        print("Creating documents...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=100, separators=["\n\n", "\n", ". ", " ", ""]
        )
        texts = text_splitter.split_text(text)
        return [
            Document(page_content=chunk, metadata={"source": video_title})
            for chunk in texts
        ]

    def create_vector_store(self, documents: List[Document]) -> Chroma:
        """Create vector store from documents"""
        print(
            f"Creating vector store using {self.embedding_model.model_type} embeddings..."
        )

        # Create vector store using LangChain's interface
        return Chroma.from_documents(
            documents=documents,
            embedding=self.embedding_model.embedding_fn,
            collection_name=f"youtube_summary_{self.embedding_model.model_type}",
        )

    def generate_summary(self, documents: List[Document]) -> str:
        """Generate summary using LangChain's summarize chain"""
        print("Generating summary...")
        map_prompt = ChatPromptTemplate.from_template(
            """Write a concise summary of the following transcript section:
            "{text}"
            CONCISE SUMMARY:"""
        )

        combine_prompt = ChatPromptTemplate.from_template(
            """Write a detailed summary of the following video transcript sections:
            "{text}"
            
            Include:
            - Main topics and key points
            - Important details and examples
            - Any conclusions or call to action
            
            DETAILED SUMMARY:"""
        )

        summary_chain = load_summarize_chain(
            llm=self.llm_model.llm,
            chain_type="map_reduce",
            map_prompt=map_prompt,
            combine_prompt=combine_prompt,
            verbose=True,
        )
        return summary_chain.invoke(documents)

    def setup_qa_chain(self, vector_store: Chroma):
        """Set up question-answering chain"""
        memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )
        return ConversationalRetrievalChain.from_llm(
            llm=self.llm_model.llm,
            retriever=vector_store.as_retriever(),
            memory=memory,
            verbose=True,
        )

    def process_video(self, url: str) -> Dict:
        """Process video and return summary and QA chain"""
        try:
            # Download transcript and process
            video_id = self.get_video_id(url)
            video_title = self.get_video_title(url)
            transcript = self.get_transcript(video_id)
            documents = self.create_documents(transcript, video_title)
            summary = self.generate_summary(documents)
            vector_store = self.create_vector_store(documents)
            qa_chain = self.setup_qa_chain(vector_store)

            return {
                "summary": summary,
                "qa_chain": qa_chain,
                "title": video_title,
                "full_transcript": transcript,
            }
        except Exception as e:
            print(f"Error processing video: {str(e)}")
            return None


def main():
    # use these urls for testing
    urls = [
        "https://www.youtube.com/watch?v=v48gJFQvE1Y",
    ]
    # Get model preferences
    print("\nAvailable LLM Models:")
    print("1. OpenAI GPT-4")
    print("2. Ollama Llama3.2")
    llm_choice = input("Choose LLM model (1/2): ").strip()

    print("\nAvailable Embeddings:")
    print("1. OpenAI")
    print("2. Chroma Default")
    print("3. Nomic (via Ollama)")
    embedding_choice = input("Choose embeddings (1/2/3): ").strip()

    # Configure model settings
    llm_type = "openai" if llm_choice == "1" else "ollama"
    llm_model_name = "gpt-6-luna" if llm_choice == "1" else "llama3.2"

    if embedding_choice == "1":
        embedding_type = "openai"
    elif embedding_choice == "2":
        embedding_type = "chroma"
    else:
        embedding_type = "nomic"

    try:
        # Initialize summarizer
        summarizer = YoutubeVideoSummarizer(
            llm_type=llm_type,
            llm_model_name=llm_model_name,
            embedding_type=embedding_type,
        )

        # Display configuration
        model_info = summarizer.get_model_info()
        print("\nCurrent Configuration:")
        print(f"LLM: {model_info['llm_type']} ({model_info['llm_model']})")
        print(f"Embeddings: {model_info['embedding_type']}")

        # Process video
        url = input("\nEnter YouTube URL: ")
        if not url:
            url = urls[0]  # Default to first URL if none provided
        print(f"\nProcessing video...")
        result = summarizer.process_video(url)

        if result:
            print(f"\nVideo Title: {result['title']}")
            print("\nSummary:")
            print(result["summary"])

            # Interactive Q&A
            print("\nYou can now ask questions about the video (type 'quit' to exit)")
            while True:
                query = input("\nYour question: ").strip()
                if query.lower() == "quit":
                    break
                if query:
                    response = result["qa_chain"].invoke({"question": query})
                    print("\nAnswer:", response["answer"])

            # Option to see full transcript
            if input("\nWant to see the full transcript? (y/n): ").lower() == "y":
                print("\nFull Transcript:")
                print(result["full_transcript"])

    except Exception as e:
        print(f"Error: {str(e)}")
        print("Make sure required models and APIs are properly configured.")


if __name__ == "__main__":
    main()
