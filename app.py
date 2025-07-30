from flask import Flask, request, jsonify, render_template
import os
import google.generativeai as genai
from google.generativeai.types import content_types
import time
import re

# Imports for Rate and Token Limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# Configure Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour"],
    storage_uri="memory://"
)

# Setup for Token Usage Limiting
USER_TOKEN_USAGE = {}
TOKEN_LIMIT_PER_HOUR = 5000

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")
genai.configure(api_key=GEMINI_API_KEY)

# Load System Context from file
try:
    with open('context.txt', 'r', encoding='utf-8') as f:
        SYSTEM_CONTEXT = f.read()
except FileNotFoundError:
    SYSTEM_CONTEXT = "You are a helpful assistant."
    app.logger.warning("Warning: context.txt not found. Using a default system context.")

# Initialize the Generative Model and the citation pattern
try:
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        system_instruction=SYSTEM_CONTEXT
    )
    # Compile the regex pattern once for efficiency
    citation_pattern = re.compile(r'\')
except Exception as e:
    app.logger.error(f"Failed to initialize GenerativeModel: {e}")
    model = None
    citation_pattern = None

# Helper functions for Token Limiting
def check_and_get_usage(user_ip):
    """Checks a user's token usage and resets it if the hour has passed."""
    current_time = time.time()
    last_reset, token_count = USER_TOKEN_USAGE.get(user_ip, (current_time, 0))

    if current_time - last_reset > 3600:
        USER_TOKEN_USAGE[user_ip] = (current_time, 0)
        return 0
    return token_count

def update_token_usage(user_ip, tokens_used):
    """Adds new token usage to the user's current total for the hour."""
    current_time = time.time()
    current_count = check_and_get_usage(user_ip)
    last_reset = USER_TOKEN_USAGE.get(user_ip, (current_time, 0))[0]
    USER_TOKEN_USAGE[user_ip] = (last_reset, current_count + tokens_used)

# --- ROUTES ---
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/ask', methods=['POST'])
@limiter.limit("10 per minute")
def ask():
    if not model:
        return jsonify({'error': 'AI 모델을 사용할 수 없습니다.'}), 503

    user_ip = get_remote_address()

    if check_and_get_usage(user_ip) >= TOKEN_LIMIT_PER_HOUR:
        return jsonify({'error': '짧은 시간 동안 너무 많이 질문하셔서 AI가 지쳤어요... 잠시 후 다시 질문해 주세요.'}), 429

    data = request.get_json()
    if not data or 'question' not in data or not data['question'].strip():
        return jsonify({'error': '질문이 제공되지 않았습니다.'}), 400

    user_question = data.get("question")
    history_data = data.get("history", [])

    try:
        history = [content_types.to_content(item) for item in history_data]
        chat = model.start_chat(history=history)

        input_tokens = model.count_tokens(chat.history + [content_types.to_content(user_question)])
        response = chat.send_message(user_question)
        output_tokens = model.count_tokens(response.text)
        
        total_tokens_used = input_tokens.total_tokens + output_tokens.total_tokens
        update_token_usage(user_ip, total_tokens_used)
        
        app.logger.info(f"User {user_ip} used {total_tokens_used} tokens.")

        # Use the compiled pattern to clean the text for the user
        clean_answer = citation_pattern.sub('', response.text).strip()
        
        return jsonify({'answer': clean_answer})

    except Exception as e:
        app.logger.error(f"An error occurred with the Gemini API for user {user_ip}: {e}")
        return jsonify({'error': 'AI와 통신하는 중 내부 오류가 발생했습니다.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
