from flask import Flask, request, jsonify, render_template
from collections import defaultdict
import os
import google.generativeai as genai

# --- ADD THIS LINE FOR DEBUGGING ---
print(f"--- Using google-generativeai version: {genai.__version__} ---") 

app = Flask(__name__)

# It's best practice to load the key only from the environment variable.
# The hardcoded key is removed to prevent security issues.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

genai.configure(api_key=GEMINI_API_KEY)

# A simple in-memory token tracker (this will reset if the app restarts)
user_tokens = defaultdict(lambda: 100) # Note: A more robust solution would use a database.

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/ask', methods=['POST'])
def ask():
    ip = request.remote_addr
    data = request.get_json()
    question = data.get("question", "")

    if not question:
        return jsonify({'error': 'No question provided.'}), 400

    if user_tokens[ip] <= 0:
        return jsonify({'error': 'Token limit reached for your IP address.'}), 429

    try:
        # --- THIS IS THE KEY CHANGE ---
         model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content(question)
        
        # A more accurate way to count would be to use the API's token count if available.
        # This is a simple approximation.
        user_tokens[ip] -= len(question.split())
        
        return jsonify({'answer': response.text})
    except Exception as e:
        # It's good practice to log the actual error for debugging
        app.logger.error(f"An error occurred: {e}")
        return jsonify({'error': 'An internal error occurred.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
