from flask import Flask, render_template, request, jsonify, session
import chromadb
import requests
import json
from dotenv import load_dotenv
import os
import uuid
import sqlite3
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key")  # Change this in production

# RAG setup
DATA_PATH = r"data"
CHROMA_PATH = r"chroma_db"

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name="Orientation")

# Configuration for Ollama
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-coder:7b")  # Update with your model

# Database setup for feedback storage
def init_db():
    conn = sqlite3.connect('feedback.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id TEXT PRIMARY KEY,
        query TEXT,
        response TEXT,
        feedback TEXT,
        timestamp TEXT
    )
    ''')
    conn.commit()
    conn.close()

def extract_final_answer(full_response):
    """Extract just the final answer from the LLM response, removing reasoning"""
    # Split by common reasoning indicators
    indicators = [
        "Therefore,", "Thus,", "In conclusion,", "So,", "To summarize,", 
        "Based on the information provided,", "According to the data,",
        "From the information,"
    ]
    
    lines = full_response.strip().split('\n')
    
    # If it's a single line, try to find reasoning indicators
    if len(lines) == 1:
        for indicator in indicators:
            if indicator.lower() in full_response.lower():
                parts = full_response.lower().split(indicator.lower(), 1)
                if len(parts) > 1:
                    return parts[1].strip().capitalize()
    
    # If multi-line, the last 1-2 lines are usually the conclusion
    elif len(lines) > 2:
        # Check if the last line is the answer
        if len(lines[-1].strip()) > 10:
            return lines[-1].strip()
        # If last line is too short, take last two lines
        elif len(lines[-1].strip()) <= 10 and len(lines) > 2:
            return ' '.join([lines[-2].strip(), lines[-1].strip()])
    
    # If we can't identify reasoning structure, return original
    return full_response

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
        raw_response = response.json()["message"]["content"]
        
        # Try to extract just the answer part
        final_answer = extract_final_answer(raw_response)
        
        return final_answer
    except requests.exceptions.RequestException as e:
        print(f"Error querying Ollama: {e}")
        return "Sorry, I encountered an error connecting to the local LLM."

@app.route('/')
def home():
    # Initialize session if not already done
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    user_query = request.json.get('query', '')
    
    if not user_query:
        return jsonify({'response': 'Please ask a question about INPT branches.'})
    
    # Query the RAG system
    results = collection.query(
        query_texts=[user_query],
        n_results=3
    )
    
    system_prompt = """
    You are a helpful assistant. You answer questions about the INPT (Institut National des Postes et Télécommunications) and its three branches: Cloud, Data, and Cybersecurity.
    You only answer based on the knowledge I provide you. You do not use your internal knowledge and you do not make things up.
    If you don't know the answer, just say: I don't know

    IMPORTANT: You must provide ONLY the direct answer to the question without showing your reasoning or thought process.
    Keep your response concise and to the point. Do not start with phrases like "Based on the information provided" or "According to the data".
    The data:
    """ + str(results['documents']) + """
    """
    
    response = query_ollama(system_prompt, user_query)
    
    # Generate a unique ID for this Q&A pair
    qa_id = str(uuid.uuid4())
    
    # Return response and ID
    return jsonify({
        'response': response,
        'qa_id': qa_id
    })

@app.route('/feedback', methods=['POST'])
def feedback():
    qa_id = request.json.get('qa_id')
    query = request.json.get('query')
    response = request.json.get('response')
    feedback_type = request.json.get('feedback')  # 'like' or 'dislike'
    
    # Store feedback in database
    conn = sqlite3.connect('feedback.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO feedback VALUES (?, ?, ?, ?, ?)",
        (qa_id, query, response, feedback_type, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/feedback/stats', methods=['GET'])
def feedback_stats():
    conn = sqlite3.connect('feedback.db')
    c = conn.cursor()
    
    # Get counts of likes and dislikes
    c.execute("SELECT feedback, COUNT(*) FROM feedback GROUP BY feedback")
    results = dict(c.fetchall())
    
    conn.close()
    
    likes = results.get('like', 0)
    dislikes = results.get('dislike', 0)
    
    return jsonify({
        'likes': likes,
        'dislikes': dislikes,
        'total': likes + dislikes
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True)