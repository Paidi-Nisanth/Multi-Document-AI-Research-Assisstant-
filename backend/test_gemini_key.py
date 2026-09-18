import os
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
print(f"Testing Gemini API Key: '{api_key[:15]}...'")

genai.configure(api_key=api_key)
try:
    model = genai.GenerativeModel("gemini-3.6-flash")
    response = model.generate_content("Say hello in 5 words.")
    print("SUCCESS Gemini Response:")
    print(response.text)
except Exception as e:
    print("ERROR calling Gemini API:")
    print(e)
