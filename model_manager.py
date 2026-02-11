from pathlib import Path
import onnxruntime as ort
import sys

APP_NAME = "LaserBaseSketch"


# ---------------------------------------------------------
# Hol van maga a program (portable app könyvtár)
# ---------------------------------------------------------
def get_app_dir():
    """
    Mindig az EXE mappáját adja vissza
    python futtatáskor: projekt könyvtár
    exe futtatáskor: exe mappa
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

MODEL_DIR = get_app_dir() / "models"


# ---------------------------------------------------------
# Model Manager
# ---------------------------------------------------------
class ModelManager:
    def __init__(self):
        self.sessions = {}

        # Megjelenő név → fájlnév
        self.registry = {
            "Téma kiemelés": "u2netp.onnx",
            #"Térmélység": "depth.onnx",
            # "Portré": "face.onnx",
            # "Épület": "structure.onnx",
        }

    # -----------------------------------------------------
    # Modell biztosítása (első indításkor másolás)
    # -----------------------------------------------------
    def _ensure_model(self, name):
        if name not in self.registry:
            return None

        filename = self.registry[name]
        source = MODEL_DIR / filename

        if not source.exists():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Hiányzó fájl",
                             f"Az AI modell nem található:\n{source}\n\n"
                             "A models mappa hiányos vagy sérült.")
            return None

        return source

    # -----------------------------------------------------
    # Session lekérése (cache-elve)
    # -----------------------------------------------------
    def get(self, name):
        if name is None:
            return None

        # már betöltve
        if name in self.sessions:
            return self.sessions[name]

        model_path = self._ensure_model(name)
        if model_path is None:
            return None

        # ONNX session létrehozás
        session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"]
        )

        self.sessions[name] = session
        return session
