import json
import os
import shutil
from pathlib import Path
from PIL import Image
import time
from google import genai
from google.genai import types

# Konfiguracja
EXERCISES_FITEBO_DIR = "exercises_fitebo"
OUTPUT_DIR = "exercises_fitebo_zdjecia"
PROGRESS_FILE = "photo_edit_progress.json"
REFERENCE_IMAGE_PATH = "reference_trainer.jpg"  # Globalne zdjęcie referencyjne dla wszystkich ćwiczeń

# Klucz API - sprawdź kolejno: zmienna środowiskowa -> plik .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# Inicjalizacja klienta Gemini (tylko jeśli klucz istnieje)
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"[!] Blad inicjalizacji klienta: {e}")


def load_progress() -> dict:
    """Wczytuje postęp z poprzedniego uruchomienia."""
    if Path(PROGRESS_FILE).exists():
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠ Nie można wczytać postępu: {e}")
    return {"processed": [], "failed": []}


def save_progress(progress: dict):
    """Zapisuje aktualny postęp."""
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠ Nie można zapisać postępu: {e}")


def process_image_with_ai(image_path: Path, output_path: Path, reference_image: Image.Image = None) -> bool:
    """
    Przetwarza pojedyncze zdjęcie używając Gemini 3 Pro Image.
    Kopiuje dokładnie strukturę oryginału ale podstawia trenera i siłownię z obrazka referencyjnego.
    
    Args:
        image_path: Ścieżka do zdjęcia do przetworzenia (DO PRZEROBIENIA)
        output_path: Ścieżka do zapisania wyniku
        reference_image: Wczytany obraz PIL z trenerem i siłownią (nie ścieżka, ale sam obraz!)
    """
    
    if reference_image is None:
        print(f"        [!] Brak obrazka referencyjnego!")
        return False
    
    prompt = """ROLA: Jesteś ekspertem od edycji obrazu i CGI (Image-to-Image Inpainting).

ZADANIE:
Masz dwa obrazki:
1. OBRAZ DOCELOWY (IMAGE 1): struktura, poza, kąt kamery, które musisz zachować 100%
2. OBRAZ ŹRÓDŁOWY (IMAGE 2): trener i siłownia, które musisz wykorzystać

INSTRUKCJE:
1. Analizuj OBRAZ DOCELOWY (IMAGE 1):
   - Zachowaj DOKŁADNIE tę samą pozę i ułożenie kończyn
   - Zachowaj DOKŁADNIE ten sam kąt kamery i perspektywę
   - Zachowaj DOKŁADNIE to samo miejsce i rozmiar postaci w kadrze
   - Zachowaj ten sam sprzęt sportowy w tej samej ręce/pozycji

2. Podstaw z OBRAZU ŹRÓDŁOWEGO (IMAGE 2):
   - Weź wygląd trenera (twarz, ciało, ubranie) z IMAGE 2
   - Weź tło siłowni z IMAGE 2 (kolory, tekstury, oświetlenie)
   - Weź styl oświetlenia z IMAGE 2

3. Połącz:
   - Postaw TRENERA z IMAGE 2 w POZIE z IMAGE 1
   - Umieść go w TŁE z IMAGE 2
   - Zachowaj GEOMETRIĘ z IMAGE 1 (kąt, perspektywę, kadrowanie)

WYMAGANIA TECHNICZNE:
- Fotorealizm (nikt nie powinien podejrzewać obróbki)
- Brak znaków wodnych
- Naturalne połączenie
- Sprzęt musi być w dokładnie tym samym miejscu jak w IMAGE 1

OUTPUT: Wygeneruj tylko obraz bez żadnego tekstu."""
    
    max_retries = 5
    base_wait_time = 2
    
    for attempt in range(max_retries):
        try:
            # Wczytaj obraz do przerobienia
            main_image = Image.open(image_path)
            
            # Przygotuj zawartość: prompt + obraz do przerobienia + referencja
            # reference_image jest już wczytany jako PIL Image
            contents = [prompt, main_image, reference_image]
            
            # Wywołaj API Gemini do wygenerowania obrazu
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE'],
                    image_config=types.ImageConfig(
                        aspect_ratio="1:1",
                        image_size="2K"
                    ),
                )
            )
            
            # Debug info
            if not response:
                print(f"        [-] Odpowiedz jest None")
            elif not hasattr(response, 'parts'):
                print(f"        [-] Brak atrybutu 'parts'")
            elif not response.parts:
                print(f"        [-] response.parts jest puste")
            
            # Wyciągnij wygenerowany obraz z odpowiedzi
            if response and hasattr(response, 'parts') and response.parts:
                for part in response.parts:
                    try:
                        if image := part.as_image():
                            # Zapisz wygenerowany obraz
                            image.save(str(output_path))
                            return True
                    except Exception as e:
                        print(f"        [-] Blad wyciagania obrazu z part: {str(e)[:100]}")
            
            # Jeśli nie znaleziono obrazu w odpowiedzi
            print(f"        [-] Brak obrazu w odpowiedzi - spróbuję ponownie")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return False
        
        except Exception as e:
            error_msg = str(e)
            
            # Sprawdź czy to błąd limitu API
            if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                if attempt < max_retries - 1:
                    wait_time = base_wait_time * (2 ** attempt)
                    print(f"        [-] Limit API - czekam {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"        [!] LIMIT API po {max_retries} probach!")
                    return False
            else:
                print(f"        [!] Blad: {str(e)[:200]}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return False
    
    return False


def process_all_images():
    """Główna funkcja przetwarzająca wszystkie zdjęcia."""
    print("=" * 70)
    print("SKRYPT EDYCJI ZDJEC CWICZEN - GEMINI 3 PRO IMAGE")
    print("=" * 70)
    
    # Sprawdź klucz API i klienta
    if not GEMINI_API_KEY or not client:
        print("\n[!] BLAD: Brak klucza API Gemini!")
        print("    Ustaw zmienna srodowiskowa:")
        print("    PowerShell: $env:GEMINI_API_KEY='twoj-klucz'")
        print("    CMD:        set GEMINI_API_KEY=twoj-klucz")
        print("    Lub:        $env:GOOGLE_API_KEY='twoj-klucz'")
        return
    
    # Sprawdź czy folder istnieje
    fitebo_dir = Path(EXERCISES_FITEBO_DIR)
    if not fitebo_dir.exists():
        print(f"\n[!] BLAD: Folder '{EXERCISES_FITEBO_DIR}' nie istnieje!")
        return
    
    # Utwórz folder wyjściowy
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)
    
    # Wczytaj postęp
    progress = load_progress()
    processed_images = set(progress.get("processed", []))
    
    if processed_images:
        print(f"\n[*] Wczytano postep: {len(processed_images)} zdjecć już przetworzonych")
    
    # Statystyki
    # Wczytaj globalne zdjęcie referencyjne
    reference_image_global = None
    reference_path = Path(REFERENCE_IMAGE_PATH)
    if reference_path.exists():
        try:
            reference_image_global = Image.open(reference_path)
            print(f"[✓] Zaladowano globalne zdjęcie referencyjne: {REFERENCE_IMAGE_PATH}")
        except Exception as e:
            print(f"[!] Błąd wczytywania referencji: {e}")
            return
    else:
        print(f"[!] Brak pliku referencyjnego: {REFERENCE_IMAGE_PATH}")
        print(f"[!] Umieść plik z trenerer i siłownią jako '{REFERENCE_IMAGE_PATH}'")
        return
    
    total_images = 0
    processed_count = 0
    failed_count = 0
    skipped_count = 0
    
    # Rozszerzenia plików graficznych
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
    
    # Przejdź przez wszystkie grupy mięśniowe
    muscle_groups = sorted([d for d in fitebo_dir.iterdir() if d.is_dir()])
    
    if not muscle_groups:
        print(f"\n[-] Brak grup miesniowych w '{EXERCISES_FITEBO_DIR}'")
        return
    
    print(f"\n[*] Znaleziono {len(muscle_groups)} grup miesniowych\n")
    
    for muscle_group_folder in muscle_groups:
        muscle_group = muscle_group_folder.name
        print(f"\n{'='*70}")
        print(f"[+] Grupa miesnniowa: {muscle_group}")
        print(f"{'='*70}")
        
        # Przejdź przez ćwiczenia w grupie
        exercise_folders = sorted([f for f in muscle_group_folder.iterdir() if f.is_dir()])
        
        if not exercise_folders:
            print(f"    [-] Brak cwiczen w grupie {muscle_group}")
            continue
        
        for exercise_folder in exercise_folders:
            exercise_name = exercise_folder.name
            print(f"\n    [*] Cwiczenie: {exercise_name}")
            
            # Znajdź wszystkie zdjęcia w folderze ćwiczenia
            image_files = sorted([
                f for f in exercise_folder.iterdir() 
                if f.is_file() and f.suffix.lower() in image_extensions
            ])
            
            if not image_files:
                print(f"        [!] Brak zdjecć")
                continue
            
            print(f"        Znaleziono {len(image_files)} zdjecć")
            
            # Utwórz folder wyjściowy dla tego ćwiczenia
            output_exercise_dir = output_dir / muscle_group / exercise_name
            output_exercise_dir.mkdir(parents=True, exist_ok=True)
            
            for img_file in image_files:
                total_images += 1
                relative_path = f"{muscle_group}/{exercise_name}/{img_file.name}"
                
                # Sprawdź czy już przetworzone
                if relative_path in processed_images:
                    skipped_count += 1
                    print(f"        [>] {img_file.name} (już przetworzone)")
                    continue
                
                output_path = output_exercise_dir / img_file.name
                
                print(f"        [*] Przetwarzam: {img_file.name}")
                
                try:
                    success = process_image_with_ai(
                        img_file, 
                        output_path, 
                        reference_image_global
                    )
                    
                    if success:
                        processed_count += 1
                        processed_images.add(relative_path)
                        print(f"        [+] Wygenerowano: {output_path}")
                    else:
                        failed_count += 1
                        progress.get("failed", []).append(relative_path)
                        print(f"        [!] Niepowodzenie")
                    
                    # Zapisz postęp po każdym zdjęciu
                    progress["processed"] = list(processed_images)
                    save_progress(progress)
                    
                    # Przerwa między zdjęciami (API rate limiting)
                    time.sleep(2)
                
                except KeyboardInterrupt:
                    print("\n\n[-] Przerwano przez uzytkownika")
                    print(f"[*] Postep zapisany: {processed_count} zdjecć przetworzonych")
                    return
                
                except Exception as e:
                    failed_count += 1
                    print(f"        [!] Blad: {str(e)[:100]}")
    
    # Raport końcowy
    print("\n" + "=" * 70)
    print("RAPORT KONCOWY")
    print("=" * 70)
    print(f"Lacznie zdjecć:           {total_images}")
    print(f"[+] Przetworzone teraz:   {processed_count}")
    print(f"[>] Pominiety (wczesniej): {skipped_count}")
    print(f"[!] Bledy:                {failed_count}")
    print(f"[*] Lacznie ukonczones:    {len(processed_images)}/{total_images}")
    print(f"\nPrzetworzone zdjecia zapisano w: {OUTPUT_DIR}/")
    print("=" * 70)


if __name__ == "__main__":
    process_all_images()
