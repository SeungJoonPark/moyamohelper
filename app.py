from flask import Flask, request, jsonify, render_template
from collections import defaultdict
import os
import google.generativeai as genai

app = Flask(__name__)

# Your Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyA7m01H5gtZIE9rXmVf2bOvoeUZTydCddE"
genai.configure(api_key=GEMINI_API_KEY)

# Token tracker per IP
user_tokens = defaultdict(lambda: 100)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/ask', methods=['POST'])
def ask():
    ip = request.remote_addr
    data = request.get_json()
    question = data.get("question", "")

    if user_tokens[ip] <= 0:
        return jsonify({'error': 'Token limit reached.'}), 429

    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(question)
        user_tokens[ip] -= len(question.split())
        return jsonify({'answer': response.text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
