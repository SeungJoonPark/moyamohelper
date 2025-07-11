from flask import Flask, render_template, request, jsonify
import openai
import os
from collections import defaultdict

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

user_tokens = defaultdict(lambda: 100)  # crude IP-based token limit

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/ask', methods=['POST'])
def ask():
    ip = request.remote_addr
    data = request.get_json()
    question = data.get("question", "")

    if user_tokens[ip] <= 0:
        return jsonify({'error': 'Token limit reached. Try tomorrow.'}), 429

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": question}]
        )
        answer = response['choices'][0]['message']['content']
        user_tokens[ip] -= len(question.split())  # crude token count
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
