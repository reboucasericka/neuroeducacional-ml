"""Seed demo data. DEVELOPMENT ONLY. Usage: python scripts/seed_demo.py"""

from __future__ import annotations

import sys
from pathlib import Path

# Garante raiz do projeto no path quando executado como script.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from src.platform.seed import seed_demo_data


def main() -> None:
    app = create_app()
    with app.app_context():
        seed_demo_data()
        print("Seed demo concluído.")


if __name__ == "__main__":
    main()
