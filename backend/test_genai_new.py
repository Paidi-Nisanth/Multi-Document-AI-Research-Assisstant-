import os
from dotenv import load_dotenv
load_dotenv()

from google import genai

api_key = os.getenv("GEMINI_API_KEY")
print(f"Testing new google-genai SDK with key: '{api_key[:15]}...'")

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Give 3 micro-architecture suggestions for mixed precision LLM inference in 3 bullet points."
)

print("\n--- NEW GOOGLE-GENAI SDK REAL OUTPUT ---")
print(response.text)
