import json
import os
import shutil
from pathlib import Path
import google.generativeai as genai
from typing import Dict, List, Any
import time
from datetime import datetime

# Konfiguracja
EXERCISES_DIR = "exercises"
OUTPUT_DIR = "exercises_translated"
PROGRESS_FILE = "translation_progress.json"
ERROR_LOG_FILE = "translation_errors.log"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inicjalizacja klienta Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Mapowania mięśni (angielski -> polski -> niemiecki)
MUSCLES_MAP = {
    "quadriceps": {"pl": "Czworogłowe ud", "de": "Quadrizeps"},
    "shoulders": {"pl": "Barki", "de": "Schultern"},
    "abdominals": {"pl": "Brzuch", "de": "Bauchmuskeln"},
    "chest": {"pl": "Klatka piersiowa", "de": "Brust"},
    "hamstrings": {"pl": "Dwugłowe ud", "de": "Hamstrings"},
    "triceps": {"pl": "Triceps", "de": "Trizeps"},
    "biceps": {"pl": "Biceps", "de": "Bizeps"},
    "lats": {"pl": "Najszersze grzbietu", "de": "Latissimus"},
    "middle back": {"pl": "Środkowe pleców", "de": "mittlerer Rücken"},
    "calves": {"pl": "Łydki", "de": "Waden"},
    "lower back": {"pl": "Lędźwie", "de": "Lenden"},
    "forearms": {"pl": "Przedramiona", "de": "Unterarme"},
    "glutes": {"pl": "Pośladki", "de": "Gesäßmuskeln"},
    "traps": {"pl": "Kaptury", "de": "Trapezmuskeln"},
    "adductors": {"pl": "Przywodziciele", "de": "Adduktoren"},
    "abductors": {"pl": "Odwodziciele", "de": "Abduktoren"},
    "neck": {"pl": "Szyja", "de": "Nacken"}
}

# Mapowania sprzętu (angielski -> polski -> niemiecki)
EQUIPMENT_MAP = {
    "barbell": {"pl": "sztanga", "de": "Langhantel"},
    "dumbbell": {"pl": "hantle", "de": "Kurzhantel"},
    "other": {"pl": "inne", "de": "Sonstiges"},
    "body only": {"pl": "masa własnego ciała", "de": "Körpergewicht"},
    "cable": {"pl": "wyciąg", "de": "Kabelzug"},
    "machine": {"pl": "maszyna", "de": "Maschine"},
    "kettlebells": {"pl": "kettlebells", "de": "Kettlebell"},
    "bands": {"pl": "gumy oporowe", "de": "Widerstandsbänder"},
    "medicine ball": {"pl": "piłka lekarska", "de": "Medizinball"},
    "exercise ball": {"pl": "piłka gimnastyczna", "de": "Gymnastikball"},
    "foam roll": {"pl": "roller", "de": "Faszienrolle"},
    "e-z curl bar": {"pl": "sztanga łamana", "de": "SZ-Stange"}
}


def log_error(message: str, error_file: str = ERROR_LOG_FILE):
    """Zapisuje błąd do pliku z logami."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(error_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")


def load_progress() -> Dict[str, bool]:
    """Wczytuje postęp z poprzedniego uruchomienia."""
    if Path(PROGRESS_FILE).exists():
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠ Nie można wczytać postępu: {e}")
    return {}


def save_progress(progress: Dict[str, bool]):
    """Zapisuje aktualny postęp."""
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠ Nie można zapisać postępu: {e}")


def map_muscles(muscles: List[str], lang: str) -> List[str]:
    """Mapuje nazwy mięśni według przygotowanej listy."""
    result = []
    for muscle in muscles:
        muscle_lower = muscle.lower()
        if muscle_lower in MUSCLES_MAP:
            result.append(MUSCLES_MAP[muscle_lower][lang])
        else:
            result.append(muscle)  # Jeśli nie ma w mapie, zachowaj oryginalną nazwę
    return result


def map_equipment(equipment: str, lang: str) -> str:
    """Mapuje nazwę sprzętu według przygotowanej listy."""
    if not equipment:  # Jeśli equipment jest None lub pusty
        return ""
    equipment_lower = equipment.lower()
    if equipment_lower in EQUIPMENT_MAP:
        return EQUIPMENT_MAP[equipment_lower][lang]
    return equipment  # Jeśli nie ma w mapie, zachowaj oryginalną nazwę


def translate_with_ai(exercise_data: Dict[str, Any], language: str) -> Dict[str, Any]:
    """
    Tłumaczy przez AI tylko: name, instructions, secondaryMuscles, category
    """
    lang_code = "pl" if language == "POLSKI" else "de"
    
    data_to_translate = {
        "name": exercise_data.get("name", ""),
        "instructions": exercise_data.get("instructions", []),
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
  "secondaryMuscles_{lang_code}": ["przetłumaczony mięsień 1", ...],
  "category_{lang_code}": "przetłumaczona kategoria"
}}"""
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                )
            )
            
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
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"    ⚠ Próba {attempt + 1} nieudana, czekam {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(f"Błąd podczas tłumaczenia AI na {language} (po {max_retries} próbach): {str(e)}")


def rename_images(exercise_folder: Path, exercise_name: str) -> int:
    """
    Zmienia nazwy plików w folderze images/ na format: nazwa_cwiczenia_0, nazwa_cwiczenia_1 itd.
    Zwraca liczbę zmienionych plików.
    """
    images_folder = exercise_folder / "images"
    if not images_folder.exists():
        return 0
    
    # Bezpieczna nazwa (bez znaków specjalnych, spacje na podkreślniki)
    safe_name = exercise_name.lower().replace(" ", "_").replace("-", "_")
    # Usuń znaki specjalne
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
    
    renamed_count = 0
    image_files = sorted(images_folder.glob("*"))
    
    for idx, img_file in enumerate(image_files):
        if img_file.is_file():
            extension = img_file.suffix  # .jpg, .png, etc.
            new_name = f"{safe_name}_{idx}{extension}"
            new_path = images_folder / new_name
            
            # Tylko jeśli nazwa jest inna
            if img_file.name != new_name:
                img_file.rename(new_path)
                renamed_count += 1
    
    return renamed_count


def process_exercise_folder(exercise_folder: Path, progress: Dict[str, bool]) -> bool:
    """
    Przetwarza folder z ćwiczeniem (exercise.json + images/).
    """
    folder_name = exercise_folder.name
    
    # Sprawdź czy folder istnieje (mógł zostać usunięty)
    if not exercise_folder.exists():
        # Usuń z postępu jeśli tam był
        if folder_name in progress:
            del progress[folder_name]
            save_progress(progress)
        return True  # Traktuj jako sukces, bo nie ma co przetwarzać
    
    # Sprawdź czy już przetworzono
    if progress.get(folder_name, False):
        print(f"\n⏩ Pomijam (już przetworzone): {folder_name}/")
        return True
    
    try:
        exercise_json = exercise_folder / "exercise.json"
        
        if not exercise_json.exists():
            error_msg = f"Brak pliku exercise.json w {folder_name}"
            print(f"  ⚠ {error_msg}")
            log_error(error_msg)
            return False
        
        print(f"\nPrzetwarzam: {folder_name}/")
        
        # Wczytaj oryginalny plik
        with open(exercise_json, 'r', encoding='utf-8') as f:
            exercise_data = json.load(f)
        
        exercise_name = exercise_data.get("name", "")
        
        # 1. Mapowanie primaryMuscles
        if "primaryMuscles" in exercise_data:
            exercise_data["primaryMuscles_pl"] = map_muscles(exercise_data["primaryMuscles"], "pl")
            exercise_data["primaryMuscles_de"] = map_muscles(exercise_data["primaryMuscles"], "de")
            print(f"  ✓ Zmapowano primaryMuscles")
        
        # 2. Mapowanie equipment
        if "equipment" in exercise_data:
            exercise_data["equipment_pl"] = map_equipment(exercise_data["equipment"], "pl")
            exercise_data["equipment_de"] = map_equipment(exercise_data["equipment"], "de")
            print(f"  ✓ Zmapowano equipment")
        
        # 3. Tłumaczenie AI (name, instructions, secondaryMuscles, category)
        print(f"  Tłumaczenie na polski...")
        polish_translation = translate_with_ai(exercise_data, "POLSKI")
        exercise_data.update(polish_translation)
        
        time.sleep(0.5)
        
        print(f"  Tłumaczenie na niemiecki...")
        german_translation = translate_with_ai(exercise_data, "NIEMIECKI")
        exercise_data.update(german_translation)
        
        # 4. Utwórz folder wyjściowy
        output_folder = Path(OUTPUT_DIR) / folder_name
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # 5. Zapisz przetłumaczony JSON (natychmiast!)
        output_json = output_folder / "exercise.json"
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(exercise_data, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Zapisano JSON")
        
        # 6. Skopiuj folder images/
        source_images = exercise_folder / "images"
        if source_images.exists():
            dest_images = output_folder / "images"
            if dest_images.exists():
                shutil.rmtree(dest_images)
            shutil.copytree(source_images, dest_images)
            
            # 7. Zmień nazwy zdjęć
            renamed = rename_images(output_folder, exercise_name)
            print(f"  ✓ Skopiowano i przemianowano {renamed} zdjęć")
        
        # 8. Zapisz postęp natychmiast po sukcesie
        progress[folder_name] = True
        save_progress(progress)
        
        print(f"  ✓ Zakończono pomyślnie")
        return True
    
    except Exception as e:
        error_msg = f"Błąd w {folder_name}: {str(e)}"
        print(f"  ✗ BŁĄD: {str(e)}")
        log_error(error_msg)
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
    
    # Wczytaj postęp z poprzedniego uruchomienia
    progress = load_progress()
    if progress:
        print(f"\n📂 Wczytano postęp: {len([v for v in progress.values() if v])} folderów już przetworzonych")
        print("   Skrypt kontynuuje od miejsca gdzie skończył.")
    
    # Znajdź wszystkie foldery z ćwiczeniami
    exercise_folders = sorted([f for f in exercises_dir.iterdir() if f.is_dir()])
    
    if not exercise_folders:
        print(f"\n⚠ Brak folderów z ćwiczeniami w '{EXERCISES_DIR}'")
        return
    
    # Policz ile zostało do zrobienia
    remaining = len([f for f in exercise_folders if not progress.get(f.name, False)])
    completed_before = len(exercise_folders) - remaining
    
    print(f"\nZnaleziono {len(exercise_folders)} folderów")
    print(f"Już przetworzone: {completed_before}")
    print(f"Do przetworzenia: {remaining}")
    
    if remaining == 0:
        print("\n✅ Wszystkie foldery już przetworzone!")
        print("Usuń plik 'translation_progress.json' aby przetworzyć ponownie.")
        return
    
    # Przetwarzaj każdy folder
    success_count = 0
    failed_count = 0
    start_time = time.time()
    
    for idx, exercise_folder in enumerate(exercise_folders, 1):
        print(f"\n[{idx}/{len(exercise_folders)}]", end=" ")
        
        if process_exercise_folder(exercise_folder, progress):
            success_count += 1
        else:
            failed_count += 1
    
    elapsed_time = time.time() - start_time
    
    # Raport końcowy
    print("\n" + "=" * 60)
    print("RAPORT KOŃCOWY")
    print("=" * 60)
    print(f"Łącznie folderów:       {len(exercise_folders)}")
    print(f"✓ Przetłumaczono teraz: {success_count}")
    print(f"✗ Błędy:                {failed_count}")
    print(f"📊 Łącznie ukończone:   {completed_before + success_count}/{len(exercise_folders)}")
    print(f"⏱  Czas wykonania:      {elapsed_time:.1f}s")
    print(f"\nPrzetłumaczone pliki zapisano w: {OUTPUT_DIR}/")
    if failed_count > 0:
        print(f"⚠  Logi błędów zapisano w: {ERROR_LOG_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
