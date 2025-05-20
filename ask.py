# Modified ask.py for using Ollama instead of OpenAI API
import chromadb
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

# setting the environment
DATA_PATH = r"data"
CHROMA_PATH = r"chroma_db"

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name="growing_vegetables")

# Configuration for Ollama
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")  # Change to your preferred model

def query_ollama(system_prompt, user_query):
    """Send a query to the Ollama API"""
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                "stream": False
            }
        )
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.json()["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"Error querying Ollama: {e}")
        return "Sorry, I encountered an error connecting to the local LLM."

def main():
    user_query = input("What do you want to know about growing vegetables?\n\n")

    results = collection.query(
        query_texts=[user_query],
        n_results=3  # Increased to 3 for more context
    )

    system_prompt = """
    You are a helpful assistant. You answer questions about growing vegetables in Florida. 
    But you only answer based on knowledge I'm providing you. You don't use your internal 
    knowledge and you don't make things up.
    If you don't know the answer, just say: I don't know
    --------------------
    The data:
    """ + str(results['documents']) + """
    """

    response = query_ollama(system_prompt, user_query)

    print("\n\n---------------------\n\n")
    print(response)

if __name__ == "__main__":
    main()