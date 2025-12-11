import json
import os
from pathlib import Path

def get_secondary_muscles():
    """Extract all unique secondary muscles from exercise.json files."""
    secondary_muscles = set()
    exercises_dir = Path(__file__).parent / "exercises"
    
    # Iterate through all subdirectories in exercises folder
    for exercise_folder in exercises_dir.iterdir():
        if exercise_folder.is_dir():
            exercise_json = exercise_folder / "exercise.json"
            
            if exercise_json.exists():
                try:
                    with open(exercise_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Get secondary muscles from the JSON
                    if 'secondaryMuscles' in data:
                        secondary_muscles.update(data['secondaryMuscles'])
                except json.JSONDecodeError as e:
                    print(f"Error reading {exercise_json}: {e}")
                except Exception as e:
                    print(f"Error processing {exercise_json}: {e}")
    
    return sorted(secondary_muscles)

if __name__ == "__main__":
    muscles = get_secondary_muscles()
    
    print("Unique Secondary Muscles:")
    print("=" * 50)
    for muscle in muscles:
        print(f"  - {muscle}")
    
    print(f"\nTotal: {len(muscles)} unique secondary muscles")
    
    # Save to file
    output_file = Path(__file__).parent / "secondary_muscles_list.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Unique Secondary Muscles\n")
        f.write("=" * 50 + "\n\n")
        for muscle in muscles:
            f.write(f"{muscle}\n")
        f.write(f"\nTotal: {len(muscles)} unique secondary muscles\n")
    
    print(f"\nResults saved to: {output_file}")
