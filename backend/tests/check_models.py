"""Lista los modelos disponibles para la cuenta configurada en GOOGLE_API_KEY."""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from google import genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("GOOGLE_API_KEY no esta configurada. Copia .env.example a .env y completa la clave.")
    sys.exit(1)

client = genai.Client(api_key=api_key)

print("Modelos disponibles en tu cuenta:")
for model in client.models.list():
    if "generateContent" in (model.supported_actions or []):
        print(f"- {model.name}")
