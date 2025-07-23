import argparse
import logging
import queue
import threading
import time
from pathlib import Path

import keyboard
import mlx.core as mx
import numpy as np
import pynput
import sounddevice as sd
import torch
import torchaudio
from mlx_whisper.transcribe import transcribe as whisper_transcribe
from pync import Notifier

from app.ui import FloatingWindow

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
SAMPLE_RATE = 16000
CHUNK_DURATION = 5  # seconds
VAD_THRESHOLD = 0.5
HOTKEY = "cmd+shift+d"

class DictationApp:
    """Main application class for the dictation tool."""

    def __init__(self, model="base", warmup=False):
        self.model_name = model
        self.warmup = warmup
        self.ui = FloatingWindow()
        self.audio_q = queue.Queue()
        self.transcript_q = queue.Queue()
        self.is_recording = False
        self.stop_event = threading.Event()
        self.language_tool = None
        self.keyboard_controller = pynput.keyboard.Controller()
        self.vad_model, _ = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')

    def run(self):
        """Main application loop."""
        self._initialize()
        self.ui.create_window()
        keyboard.add_hotkey(HOTKEY, self.toggle_recording)

        try:
            while not self.stop_event.is_set():
                event, values = self.ui.window.read(timeout=100)
                if event == sg.WIN_CLOSED:
                    break
                if event == '-REC-':
                    self.start_recording()
                if event == '-STOP-':
                    self.stop_recording()

                self.ui.pulse_record_button(self.is_recording)
                self._update_level_meter()

        except KeyboardInterrupt:
            logging.info("Ctrl-C pressed. Shutting down.")
        finally:
            self.shutdown()

    def _initialize(self):
        """Initializes models and other components."""
        logging.info(f"Loading Whisper model: {self.model_name}")
        if self.warmup:
            whisper_transcribe(str(Path(__file__).parent / "warmup.wav"), model=self.model_name)
            logging.info("Whisper model warmed up.")

        try:
            import language_tool_python
            self.language_tool = language_tool_python.LanguageTool('en-US')
            logging.info("LanguageTool loaded.")
        except ImportError:
            logging.warning("language_tool_python not found. Post-processing will be disabled.")

    def toggle_recording(self):
        """Toggles the recording state."""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        """Starts audio recording and transcription threads."""
        if self.is_recording:
            return
        logging.info("Starting recording...")
        self.is_recording = True
        self.audio_q = queue.Queue()
        self.transcript_q = queue.Queue()

        self.audio_thread = threading.Thread(target=self._audio_capture_thread)
        self.transcription_thread = threading.Thread(target=self._transcription_thread)
        self.audio_thread.start()
        self.transcription_thread.start()

    def stop_recording(self):
        """Stops audio recording and processes the final transcript."""
        if not self.is_recording:
            return
        logging.info("Stopping recording...")
        self.is_recording = False
        self.audio_thread.join()
        self.transcription_thread.join()

        full_transcript = " ".join(list(self.transcript_q.queue))
        self._process_and_output(full_transcript)

    def _audio_capture_thread(self):
        """Captures audio from the microphone and puts it into a queue."""
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32', callback=self._audio_callback):
            while self.is_recording:
                time.sleep(0.1)

    def _audio_callback(self, indata, frames, time, status):
        """Callback function for the audio stream."""
        if status:
            logging.warning(f"Audio stream status: {status}")
        self.audio_q.put(indata.copy())

    def _update_level_meter(self):
        """Updates the UI level meter from the audio queue."""
        if not self.audio_q.empty():
            data = self.audio_q.get()
            rms = np.sqrt(np.mean(data**2))
            level = int(rms * 500)
            self.ui.update_level_meter(level)

    def _transcription_thread(self):
        """Transcribes audio chunks from the queue using Whisper."""
        while self.is_recording:
            try:
                audio_chunk = self._get_audio_chunk()
                if audio_chunk is not None:
                    self._transcribe_chunk(audio_chunk)
            except queue.Empty:
                time.sleep(0.1)

    def _get_audio_chunk(self):
        """Gets a chunk of audio from the queue with VAD."""
        audio_buffer = []
        start_time = time.time()
        while time.time() - start_time < CHUNK_DURATION:
            try:
                data = self.audio_q.get(timeout=0.1)
                audio_buffer.append(data)
            except queue.Empty:
                if not self.is_recording:
                    break
                continue

        if not audio_buffer:
            return None

        audio_tensor = torch.from_numpy(np.concatenate(audio_buffer)).float()
        is_speech = self.vad_model(audio_tensor, SAMPLE_RATE).item() >= VAD_THRESHOLD
        return audio_tensor if is_speech else None

    def _transcribe_chunk(self, audio_chunk):
        """Transcribes a single audio chunk."""
        temp_file = Path("temp_audio.wav")
        torchaudio.save(str(temp_file), audio_chunk.unsqueeze(0), SAMPLE_RATE)
        try:
            result = whisper_transcribe(str(temp_file), model=self.model_name)
            if result["text"]:
                self.transcript_q.put(result["text"].strip())
                logging.info(f"Transcript chunk: {result['text']}")
        finally:
            temp_file.unlink()

    def _process_and_output(self, text):
        """Post-processes the transcript and outputs it."""
        if not text:
            logging.info("Empty transcript. Nothing to output.")
            return

        if self.language_tool:
            try:
                text = self.language_tool.correct(text)
                logging.info(f"Corrected transcript: {text}")
            except Exception as e:
                logging.error(f"Error during language correction: {e}")

        self.keyboard_controller.type(text)
        Notifier.notify(text, title="Dictation Complete")
        logging.info(f"Final transcript: {text}")

    def shutdown(self):
        """Cleans up resources and closes the application."""
        logging.info("Shutting down...")
        self.stop_event.set()
        if self.is_recording:
            self.stop_recording()
        self.ui.close()
        if self.language_tool:
            self.language_tool.close()
        sd.stop()

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="A push-to-talk dictation tool using Whisper.")
    parser.add_argument("--model", type=str, default="base", choices=["tiny", "base", "small"],
                        help="Whisper model to use.")
    parser.add_argument("--warmup", action="store_true",
                        help="Warm up the Whisper model on startup.")
    args = parser.parse_args()

    app = DictationApp(model=args.model, warmup=args.warmup)
    app.run()

if __name__ == "__main__":
    main()
