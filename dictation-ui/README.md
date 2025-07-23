# Dictation UI

A polished, push-to-talk dictation tool for macOS backed by Whisper. This tool provides a simple floating UI to start and stop dictation, and it injects the transcribed text into the currently focused application.

## Features

-   **Offline Transcription**: Uses `mlx-whisper` for fast, local, and private transcription.
-   **Floating UI**: A semi-transparent, always-on-top window with recording controls.
-   **Global Hotkey**: Toggle recording with `⌘ + Shift + D`.
-   **Voice Activity Detection**: Uses Silero VAD to reduce unnecessary processing.
-   **Real-time Transcription**: Transcribes audio in chunks for a responsive experience.
-   **Post-processing**: Automatically corrects casing and punctuation using `language-tool-python`.
-   **Desktop Notifications**: Shows the final transcript as a macOS notification.

## Requirements

-   macOS 15.1.1 or later
-   Apple Silicon (M-series) Mac
-   Homebrew

## Installation

1.  **Install System Dependencies**:
    Open your terminal and install PortAudio, a required dependency for `sounddevice`:
    ```bash
    brew install portaudio
    ```

2.  **Set up a Virtual Environment**:
    It's recommended to install the Python packages in a virtual environment.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Python Packages**:
    Install all required packages using pip:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the application from the root of the project directory:

```bash
python -m app.dictate
```

### CLI Options

-   `--model {tiny,base,small}`: Specify the Whisper model to use. Defaults to `base`.
    ```bash
    python -m app.dictate --model small
    ```
-   `--warmup`: Pre-load and warm up the Whisper model on startup for faster initial transcription.
    ```bash
    python -m app.dictate --warmup
    ```

### How to Use the UI

1.  **Start the app**: A small, floating window will appear in the top-right corner of your screen.
2.  **Toggle Recording**:
    -   Press `⌘ + Shift + D` to start or stop recording.
    -   Alternatively, click the red **●** button to start and the green **■** button to stop.
3.  **Dictate**: While recording, the red button will pulse. Speak clearly into your microphone.
4.  **Get Transcript**: When you stop recording, the transcribed text will be typed into your active application window.

## Troubleshooting

### macOS Permissions

On the first run, macOS will prompt you for two permissions:

1.  **Microphone Access**: Required for audio recording.
2.  **Accessibility Access**: Required to simulate keystrokes for text injection and to monitor for the global hotkey.

If you deny these permissions accidentally, you can grant them later in:
`System Settings` > `Privacy & Security` > `Microphone` and `Accessibility`.

### `language_tool_python` Issues

The language tool requires a running Java instance. If you encounter issues, you can run the application without it. The app will gracefully fall back to using the raw Whisper transcript.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
