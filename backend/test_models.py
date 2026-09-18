import os
from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
print(f"Key starts with: {api_key[:10]}")

genai.configure(api_key=api_key)
try:
    models = list(genai.list_models())
    print("Available Models:")
    for m in models:
        print(f" - {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
