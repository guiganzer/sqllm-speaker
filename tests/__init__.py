"""Permite executar testes sem instalar o pacote durante a fase de fundação."""

from pathlib import Path
import sys

SOURCE_DIRECTORY = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_DIRECTORY))
