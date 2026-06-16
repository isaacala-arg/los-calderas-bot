import sys
import os

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("ERROR: Pon tu key así:\n  $env:GEMINI_API_KEY='tu-key-aqui'")
    sys.exit(1)

print(f"Probando key: {api_key[:8]}...{api_key[-4:]}")

try:
    from google import genai
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Di exactamente: FUNCIONA",
    )
    print(f"Respuesta de Gemini: {response.text.strip()}")
    print("\n✅ LA KEY FUNCIONA")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
