import json
import os
from pathlib import Path
import google.generativeai as genai
from typing import Dict, List, Any
import time

# Konfiguracja
EXERCISES_DIR = "exercises"
OUTPUT_DIR = "exercises_translated"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Ustaw zmienną środowiskową GEMINI_API_KEY

# Inicjalizacja klienta Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')


def translate_exercise(exercise_data: Dict[str, Any], language: str) -> Dict[str, Any]:
    """
    Tłumaczy dane ćwiczenia na wybrany język używając Gemini API.
    
    Args:
        exercise_data: Słownik z danymi ćwiczenia
        language: "POLSKI" lub "NIEMIECKI"
    
    Returns:
        Słownik z przetłumaczonymi danymi
    """
    lang_code = "pl" if language == "POLSKI" else "de"
    
    # Przygotuj dane do tłumaczenia
    data_to_translate = {
        "name": exercise_data.get("name", ""),
        "instructions": exercise_data.get("instructions", []),
        "primaryMuscles": exercise_data.get("primaryMuscles", []),
        "secondaryMuscles": exercise_data.get("secondaryMuscles", []),
        "category": exercise_data.get("category", "")
    }
    
    prompt = f"""Tłumacz dokładnie to ćwiczenie na język {language}. Zwróć TYLKO JSON z tłumaczeniami bez dodatkowego tekstu.
Zachowaj wszystkie nazwy mięśni jako fizjologiczne terminy. Tłumaczenia muszą być dokładne i profesjonalne.

Oryginalne dane:
{json.dumps(data_to_translate, ensure_ascii=False, indent=2)}

Zwróć JSON w formacie:
{{
  "name_{lang_code}": "przetłumaczona nazwa",
  "instructions_{lang_code}": ["przetłumaczona instrukcja 1", "przetłumaczona instrukcja 2", ...],
  "primaryMuscles_{lang_code}": ["przetłumaczony mięsień 1", ...],
  "secondaryMuscles_{lang_code}": ["przetłumaczony mięsień 1", ...],
  "category_{lang_code}": "przetłumaczona kategoria"
}}"""
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
            )
        )
        
        # Wyczyść odpowiedź z potencjalnych znaczników markdown
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        translation = json.loads(response_text)
        return translation
    
    except Exception as e:
        raise Exception(f"Błąd podczas tłumaczenia na {language}: {str(e)}")


def process_exercise_file(file_path: Path) -> bool:
    """
    Przetwarza pojedynczy plik JSON z ćwiczeniem.
    
    Args:
        file_path: Ścieżka do pliku JSON
    
    Returns:
        True jeśli sukces, False w przypadku błędu
    """
    try:
        print(f"\nPrzetwarzam: {file_path.name}")
        
        # Wczytaj oryginalny plik
        with open(file_path, 'r', encoding='utf-8') as f:
            exercise_data = json.load(f)
        
        # Tłumacz na polski
        print(f"  Tłumaczenie na polski...")
        polish_translation = translate_exercise(exercise_data, "POLSKI")
        exercise_data.update(polish_translation)
        
        # Krótka przerwa między requestami
        time.sleep(0.5)
        
        # Tłumacz na niemiecki
        print(f"  Tłumaczenie na niemiecki...")
        german_translation = translate_exercise(exercise_data, "NIEMIECKI")
        exercise_data.update(german_translation)
        
        # Zapisz przetłumaczony plik
        output_path = Path(OUTPUT_DIR) / file_path.name
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(exercise_data, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ Zakończono pomyślnie")
        return True
    
    except Exception as e:
        print(f"  ✗ BŁĄD: {str(e)}")
        return False


def main():
    """Główna funkcja skryptu."""
    print("=" * 60)
    print("SKRYPT TŁUMACZENIA ĆWICZEŃ")
    print("=" * 60)
    
    # Sprawdź klucz API
    if not GEMINI_API_KEY:
        print("\n❌ BŁĄD: Brak klucza API Gemini!")
        print("Ustaw zmienną środowiskową GEMINI_API_KEY")
        print("Przykład: $env:GEMINI_API_KEY='twój-klucz-api'")
        return
    
    # Sprawdź czy folder exercises istnieje
    exercises_dir = Path(EXERCISES_DIR)
    if not exercises_dir.exists():
        print(f"\n❌ BŁĄD: Folder '{EXERCISES_DIR}' nie istnieje!")
        return
    
    # Utwórz folder wyjściowy jeśli nie istnieje
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)
    
    # Znajdź wszystkie pliki JSON
    json_files = list(exercises_dir.glob("*.json"))
    
    if not json_files:
        print(f"\n⚠ Brak plików JSON w folderze '{EXERCISES_DIR}'")
        return
    
    print(f"\nZnaleziono {len(json_files)} plików JSON do przetworzenia")
    
    # Przetwarzaj każdy plik
    success_count = 0
    failed_count = 0
    
    for json_file in json_files:
        if process_exercise_file(json_file):
            success_count += 1
        else:
            failed_count += 1
    
    # Raport końcowy
    print("\n" + "=" * 60)
    print("RAPORT KOŃCOWY")
    print("=" * 60)
    print(f"Łącznie plików:          {len(json_files)}")
    print(f"✓ Przetłumaczono:        {success_count}")
    print(f"✗ Błędy:                 {failed_count}")
    print(f"\nPrzetłumaczone pliki zapisano w: {OUTPUT_DIR}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
