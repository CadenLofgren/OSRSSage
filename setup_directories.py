"""
Setup script to create necessary directories.
"""

from pathlib import Path

directories = [
    "data/raw",
    "data/processed",
    "data/vector_db",
    "logs"
]

for directory in directories:
    Path(directory).mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {directory}")

print("\nAll directories created!")
