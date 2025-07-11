from flask import Flask, request, jsonify, render_template
import os
import google.generativeai as genai

app = Flask(__name__)

# --- It's helpful to see the library version in the logs during setup ---
# You can remove this line in production if you wish.
print(f"--- Using google-generativeai version: {genai.__version__} ---")

# --- Configuration ---
# Load the API key from environment variables for security.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")
genai.configure(api_key=GEMINI_API_KEY)

# --- Load System Context ---
# Read the instructions for the AI from the context.txt file.
# This is done once when the application starts.
try:
    with open('context.txt', 'r', encoding='utf-8') as f:
        SYSTEM_CONTEXT = f.read()
except FileNotFoundError:
    # If the context file is missing, provide a default or raise an error.
    SYSTEM_CONTEXT = "당신은 '식물 집사'라는 이름의 식물 및 정원 가꾸기 전문가입니다. 당신의 임무는 식물이나 정원 가꾸기와 관련된 질문에만 친절하고 상세하게 답변하는 것입니다. 만약 사용자의 질문이 식물이나 정원 가꾸기와 관련이 없다면, '저는 식물과 정원 가꾸기에 대한 질문에만 답변할 수 있어요.'라고 정중히 거절해야 합니다.\n\n사용자 질문: "
    print("Warning: context.txt not found. Using default system context.")


# --- Routes ---
@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template("index.html")

@app.route('/ask', methods=['POST'])
def ask():
    """Receives a question, combines it with the system context, and asks the Gemini API."""
    data = request.get_json()
    if not data or 'question' not in data or not data['question'].strip():
        return jsonify({'error': 'No question provided.'}), 400

    user_question = data.get("question")

    # Combine the pre-loaded system context with the new user question.
    full_prompt = SYSTEM_CONTEXT + f'"{user_question}"'

    try:
        # Use the full prompt to generate content.
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(full_prompt)
        return jsonify({'answer': response.text})
    except Exception as e:
        # Log the detailed error on the server for debugging.
        app.logger.error(f"An error occurred with the Gemini API: {e}")
        # Return a generic error to the user.
        return jsonify({'error': 'An internal error occurred while processing the request.'}), 500

if __name__ == '__main__':
    # Using port 8080 is a common practice for web services on platforms like Render.
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
