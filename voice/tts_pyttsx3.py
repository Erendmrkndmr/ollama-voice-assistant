# voice/tts_pyttsx3.py
import pyttsx3

_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        # İstersen ses/hız ayarı:
        # _engine.setProperty('rate', 180)
        # _engine.setProperty('volume', 1.0)
    return _engine

def speak(text: str):
    eng = _get_engine()
    eng.say(text)
    eng.runAndWait()
