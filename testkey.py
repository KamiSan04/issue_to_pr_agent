import os
from dotenv import load_dotenv
from google import genai

load_dotenv() 

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not found. Check your .env file.")

model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model=model,
    contents="Say hello in 5 words.",
)
print(response.text)