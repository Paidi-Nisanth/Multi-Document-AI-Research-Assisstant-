import os
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
print(f"Testing Gemini 3.6 Flash Key: '{api_key[:15]}...'")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

res = model.generate_content("Give me 3 suggestions for micro-architecture in mixed precision LLM inference.")
print("\n--- GEMINI 3.6 FLASH REAL LLM OUTPUT ---")
print(res.text)
