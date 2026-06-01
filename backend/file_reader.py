from pathlib import Path

START_PATH = Path(".")
OUTPUT_FILE = "all_files.txt"

ignored_dirs = {
    ".git",
    "venv",
    "__pycache__",
    "node_modules"
}

count = 0

with open(OUTPUT_FILE, "w", encoding="utf-8") as output:

    for path in START_PATH.rglob("*"):

        if not path.is_file():
            continue

        if any(part in ignored_dirs for part in path.parts):
            continue

        print(f"READING: {path}")

        try:
            content = path.read_text(encoding="utf-8")

            output.write(f"\n{'=' * 80}\n")
            output.write(f"FILE: {path}\n")
            output.write(f"{'=' * 80}\n\n")
            output.write(content)
            output.write("\n\n")

            count += 1

        except Exception as e:
            print(f"ERROR: {path} -> {e}")

print(f"\nDONE. {count} FILES WRITTEN.")
print(f"OUTPUT: {OUTPUT_FILE}")