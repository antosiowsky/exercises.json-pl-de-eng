# Skrypt do sprawdzenia dostępnych modeli Gemini
import google.generativeai as genai
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ BŁĄD: Brak klucza API!")
    print("Ustaw: $env:GEMINI_API_KEY='twój-klucz'")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

try:
    print("Szukam dostępnych modeli Gemini...\n")
    print("Modele obsługujące generateContent:")
    print("-" * 50)
    
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✓ {m.name}")
    
    print("-" * 50)
    print("\nMożesz użyć któregokolwiek z powyższych modeli.")
    
except Exception as e:
    print(f"❌ Błąd: {e}")
