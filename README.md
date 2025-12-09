# Skrypt Tłumaczenia Ćwiczeń

## Opis
Skrypt automatycznie tłumaczy pliki JSON z ćwiczeniami na język polski i niemiecki używając Google Gemini API (model gemini-pro).

## Wymagania
- Python 3.7+
- Biblioteka `google-generativeai`
- Klucz API Google Gemini

## Instalacja

1. Zainstaluj wymagane biblioteki:
```bash
pip install google-generativeai
```

2. Ustaw klucz API Gemini jako zmienną środowiskową:
```powershell
$env:GEMINI_API_KEY='twój-klucz-api-gemini'
```

## Struktura plików

```
exercises.json-pl-de-eng/
├── translate_exercises.py    # Główny skrypt
├── exercises/                 # Folder z oryginalnymi plikami JSON
│   ├── exercise1.json
│   ├── exercise2.json
│   └── ...
└── exercises_translated/      # Folder z przetłumaczonymi plikami (generowany automatycznie)
    ├── exercise1.json
    ├── exercise2.json
    └── ...
```

## Użycie

1. Umieść pliki JSON z ćwiczeniami w folderze `exercises/`
2. Uruchom skrypt:
```bash
python translate_exercises.py
```

## Format pliku JSON

### Wejście (oryginalny plik):
```json
{
  "name": "Exercise Name",
  "force": "pull",
  "level": "beginner",
  "mechanic": "compound",
  "equipment": "barbell",
  "primaryMuscles": ["muscle1", "muscle2"],
  "secondaryMuscles": ["muscle3"],
  "instructions": ["instruction 1", "instruction 2"],
  "category": "strength"
}
```

### Wyjście (przetłumaczony plik):
```json
{
  "name": "Exercise Name",
  "name_pl": "Nazwa Ćwiczenia",
  "name_de": "Übungsname",
  "force": "pull",
  "level": "beginner",
  "mechanic": "compound",
  "equipment": "barbell",
  "primaryMuscles": ["muscle1", "muscle2"],
  "primaryMuscles_pl": ["mięsień1", "mięsień2"],
  "primaryMuscles_de": ["Muskel1", "Muskel2"],
  "secondaryMuscles": ["muscle3"],
  "secondaryMuscles_pl": ["mięsień3"],
  "secondaryMuscles_de": ["Muskel3"],
  "instructions": ["instruction 1", "instruction 2"],
  "instructions_pl": ["instrukcja 1", "instrukcja 2"],
  "instructions_de": ["Anleitung 1", "Anleitung 2"],
  "category": "strength",
  "category_pl": "siła",
  "category_de": "Kraft"
}
```

## Funkcje

- ✅ Automatyczne tłumaczenie na polski i niemiecki
- ✅ Obsługa błędów - kontynuuje przy niepowodzeniu pojedynczego pliku
- ✅ Raport końcowy z liczbą przetworzonych i błędnych plików
- ✅ Zachowanie oryginalnej struktury JSON
- ✅ Profesjonalne tłumaczenia terminologii medycznej i fitness
- ✅ Automatyczne tworzenie folderu wyjściowego

## Uwagi

- Skrypt używa modelu `gemini-pro` (dostępny w Google AI Studio)
- Między requestami jest 0.5s przerwa, aby uniknąć limitów API
- Wszystkie pliki są kodowane w UTF-8 dla obsługi polskich i niemieckich znaków
- Gemini Pro jest darmowy w ramach limitu API
