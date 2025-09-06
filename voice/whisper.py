# voice/whisper.py
# Real-time-ish recording with WebRTC VAD endpointing, then faster-whisper transcription.

import os
import sys
import time
import queue
from functools import lru_cache
from typing import Optional

import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.getenv("ENV_FILE", ".env"))

# --------- Audio config (env-overridable) ---------
RATE = 16000              # Whisper & VAD standard
CHANNELS = 1
DTYPE = "int16"           # VAD needs 16-bit PCM
FRAME_MS = int(os.getenv("VAD_FRAME_MS", "20"))          # 10/20/30 allowed for VAD
BLOCKSIZE = int(RATE * FRAME_MS / 1000)                  # samples per frame
VAD_AGGR = int(os.getenv("VAD_AGGRESSIVENESS", "2"))     # 0..3 (3 = most aggressive)
START_TRIG_FRAMES = int(os.getenv("VAD_START_FRAMES", "3"))  # start after N speech frames
END_SIL_MS = int(os.getenv("VAD_END_SIL_MS", "600"))     # stop after this much silence
MAX_SECONDS = float(os.getenv("VAD_MAX_SECONDS", "30.0"))     # hard cap per utterance
STT_LANG = os.getenv("STT_LANG")  # e.g., "tr" to lock Turkish
STT_FORCE_LANG = os.getenv("STT_FORCE_LANG", "True").lower() == "true"
STT_TASK = os.getenv("STT_TASK", "transcribe")  # 'transcribe' or 'translate'
STT_MODEL_SIZE = os.getenv("STT_MODEL_SIZE", "base")
STT_BEAM_SIZE = int(os.getenv("STT_BEAM_SIZE", "5"))
STT_TEMPERATURE = float(os.getenv("STT_TEMPERATURE", "0.0"))
STT_NO_SPEECH_THRESH = float(os.getenv("STT_NO_SPEECH_THRESH", "0.6"))
STT_PATIENCE = float(os.getenv("STT_PATIENCE", "1.0"))
STT_CONDITION_PREV = os.getenv("STT_CONDITION_PREV", "True").lower() == "true"




assert FRAME_MS in (10, 20, 30), "VAD_FRAME_MS must be 10, 20, or 30"

# --------- Utilities ---------
def _int16_pcm(audio_f32: np.ndarray) -> np.ndarray:
    audio_f32 = np.clip(audio_f32, -1.0, 1.0)
    return (audio_f32 * 32767.0).astype(np.int16)

def _float32_pcm(audio_i16: np.ndarray) -> np.ndarray:
    return audio_i16.astype(np.float32) / 32768.0


# sıcaklık fallback'lerini listeye çevir
def _parse_temps(s: str):
    try:
        return [float(x.strip()) for x in s.split(",") if x.strip() != ""]
    except Exception:
        return [float(os.getenv("STT_TEMPERATURE", "0.0"))]

STT_TEMPERATURE_LIST = _parse_temps(os.getenv("STT_TEMPERATURE_FALLBACKS", "0.0"))


# --------- Recorder with WebRTC VAD endpointing ---------
def record_until_silence() -> np.ndarray:
    """
    Opens mic, waits for speech start (N speech frames),
    records until END_SIL_MS of non-speech, or MAX_SECONDS cap.
    Returns a single int16 PCM numpy array (mono, 16 kHz).
    """
    vad = webrtcvad.Vad(VAD_AGGR)
    q: "queue.Queue[np.ndarray]" = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        # indata is float32 [-1,1] by default; request int16 stream
        q.put(indata.copy())

    print("[🎙️] Listening... speak naturally; pause to finish.")
    started = False
    speech_run = 0
    silence_run = 0
    speech_frames = []
    start_time = time.time()

    with sd.InputStream(samplerate=RATE, channels=CHANNELS,
                        dtype="float32", blocksize=BLOCKSIZE, callback=callback):
        while True:
            # timeout so we can honor MAX_SECONDS even if mic blocks
            try:
                audio_f32 = q.get(timeout=0.5).flatten()
            except queue.Empty:
                audio_f32 = np.zeros(BLOCKSIZE, dtype=np.float32)

            audio_i16 = _int16_pcm(audio_f32)

            # VAD wants bytes of 16-bit little-endian mono at 8/16/32kHz
            is_speech = vad.is_speech(audio_i16.tobytes(), RATE)

            if not started:
                if is_speech:
                    speech_run += 1
                    if speech_run >= START_TRIG_FRAMES:
                        started = True
                        speech_frames.extend([audio_i16])  # include the current frame
                        # print("[VAD] speech started")
                else:
                    speech_run = 0
            else:
                # already started
                speech_frames.append(audio_i16)
                if is_speech:
                    silence_run = 0
                else:
                    silence_run += 1
                    if silence_run * FRAME_MS >= END_SIL_MS:
                        # print("[VAD] end-of-utterance")
                        break

            # hard cap
            if time.time() - start_time >= MAX_SECONDS:
                # print("[VAD] max seconds reached")
                break

    if not speech_frames:
        print("[…] No speech detected.")
        return np.array([], dtype=np.int16)

    audio = np.concatenate(speech_frames)
    return audio

# --------- Whisper loader (offline-first via WHISPER_MODEL_PATH) ---------
@lru_cache(maxsize=1)
def get_model(model_size: str = "base") -> WhisperModel:
    local_path = os.getenv("WHISPER_MODEL_PATH")
    if local_path:
        print(f"[⏳] Loading Whisper model (local): {local_path}")
        return WhisperModel(local_path, device="cpu", compute_type="int8", local_files_only=True)
    print(f"[⏳] Loading Whisper model by name: {model_size} (cpu/int8)")
    return WhisperModel(model_size, device="cpu", compute_type="int8")  # may try online

def transcribe(audio_pcm_i16: np.ndarray, model_size: str = STT_MODEL_SIZE, language: Optional[str] = STT_LANG) -> str:
    if audio_pcm_i16.size == 0:
        return ""
    model = get_model(model_size=model_size)
    audio_f32 = _float32_pcm(audio_pcm_i16)

    lang_to_use = (language or "tr") if STT_FORCE_LANG else language

    # temperature değerini tekil ya da liste olarak hazırlayalım
    # faster-whisper 'temperature' parametresi float da alır, liste de alır
    temperature_arg = (
        STT_TEMPERATURE_LIST if (len(STT_TEMPERATURE_LIST) > 1 or STT_TEMPERATURE_LIST[0] != STT_TEMPERATURE)
        else STT_TEMPERATURE
    )

    segments, info = model.transcribe(
        audio_f32,
        language=lang_to_use,
        task=STT_TASK,  # 'transcribe'
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        beam_size=STT_BEAM_SIZE,
        patience=STT_PATIENCE,
        temperature=temperature_arg,          # <<< tek anahtar
        no_speech_threshold=STT_NO_SPEECH_THRESH,
        condition_on_previous_text=STT_CONDITION_PREV,
        without_timestamps=True,
        initial_prompt="English conversational transcript; use correct grammar and punctuation."
    )
    text = "".join(seg.text for seg in segments).strip()
    return text



if __name__ == "__main__":
    pcm = record_until_silence()
    if pcm.size == 0:
        sys.exit(0)
    text = transcribe(pcm, model_size="base", language=STT_LANG or "tr")
    print(f"[📝] STT: {text}")
