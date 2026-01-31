import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

def chat_with_context(query, context):
    prompt = f"""
You are an intelligent assistant.

Context:
{context}

User:
{query}
"""

    res = requests.post(
        OLLAMA_URL,
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
    )

    return res.json()["response"]
