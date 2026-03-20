import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

with open('models_list.txt', 'w') as f:
    try:
        for m in genai.list_models():
            f.write(f"{m.name}\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
