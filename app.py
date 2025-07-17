from flask import Flask, request, jsonify, render_template
import os
import google.generativeai as genai
# NEW: Import content_types for handling chat history format
from google.generativeai.types import content_types

app = Flask(__name__)

# --- Configuration ---
# Load API key from environment variables.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")
genai.configure(api_key=GEMINI_API_KEY)


# --- Load System Context & Initialize Model (Once at Startup) ---
try:
    with open('context.txt', 'r', encoding='utf-8') as f:
        SYSTEM_CONTEXT = f.read()
except FileNotFoundError:
    SYSTEM_CONTEXT = "당신은 '식물 집사'라는 이름의 식물 및 정원 가꾸기 전문가입니다. 당신의 임무는 식물이나 정원 가꾸기와 관련된 질문에만 친절하고 상세하게 답변하는 것입니다. 만약 사용자의 질문이 식물이나 정원 가꾸기와 관련이 없다면, '저는 식물과 정원 가꾸기에 대한 질문에만 답변할 수 있어요.'라고 정중히 거절해야 합니다."
    app.logger.warning("Warning: context.txt not found. Using default system context.")

# Initialize the model once when the app starts.
try:
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        system_instruction=SYSTEM_CONTEXT
    )
except Exception as e:
    app.logger.error(f"Failed to initialize GenerativeModel: {e}")
    model = None # Handle cases where initialization might fail.


# --- Routes ---
@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template("index.html")

# --- MODIFIED ROUTE ---
@app.route('/ask', methods=['POST'])
def ask():
    """Receives a question AND conversation history, and continues the chat."""
    if not model:
        return jsonify({'error': 'The generative model is not available.'}), 503

    data = request.get_json()
    if not data or 'question' not in data or not data['question'].strip():
        return jsonify({'error': 'No question provided.'}), 400

    user_question = data.get("question")
    # Get the history from the client, default to an empty list if it's the first message.
    history_data = data.get("history", [])

    try:
        # Convert the client-side history into the format the SDK expects.
        history = [content_types.to_content(item) for item in history_data]

        # Start a chat session with the existing history.
        chat = model.start_chat(history=history)

        # Send only the new message. The chat object remembers the rest.
        response = chat.send_message(user_question)

        return jsonify({'answer': response.text})
    except Exception as e:
        app.logger.error(f"An error occurred with the Gemini API: {e}")
        return jsonify({'error': 'An internal error occurred while processing the request.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
