# Maximus AI Assistant

Maximus is a powerful, voice-activated desktop assistant powered by Google's Gemini API (Gemini 2.0 Flash). It can perform various tasks such as answering questions include math, playing YouTube videos, checking weather, and more.


## Features
- **Voice assistant**: Uses `pyttsx3` TTS + `SpeechRecognition` for seamless voice interaction.
- **NEW: Text input mode**: Option for keyboard input when voice isn't suitable.
- **Auto language detect + translate**: Automatically detects and translates languages using `googletrans` + `langdetect` [requires internet].
- **Math solving**: Solves symbolic derivatives, integrals, and equations using `sympy`.
- **Weather**: Checks weather via `wttr.in`/Open-Meteo [requires internet].
- **YouTube play**: Plays videos directly using `pywhatkit.playonyt` [requires internet].
- **Gmail unread**: Checks unread emails (requires `credentials.json`).
- **WhatsApp send**: Sends WhatsApp messages using `pywhatkit` (uses web.whatsapp scheduling).
- **Wikipedia search**: Fetches summaries from Wikipedia.
- **Maps navigation**: Opens directions in the browser.
- **To-dos, alarms, reminders**: Manages tasks and sets alarms/reminders .
- **File & system controls**: Create, open, and delete files; open applications.
- **Memory mode**: Uses local JSON to remember facts and small details.
- **Fun jokes/facts**: tells jokes and random facts using `pyjokes` / useless facts API.
- **Optional OCR**: Reads text from images using `pytesseract` (requires Tesseract installation).
- **Robust error handling & help command**: enhanced stability and user guidance.
- **Gemini-powered witty responses**: Uses Google Gemini 2.0 for intelligent, conversational responses.
- **Wake word listener**: Always listening for the wake word to activate.
- **ALL OUTPUTS ARE NOW SPOKEN**: full voice feedback for all actions.

## Setup

1.  **Install Python 3.10+**
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Environment Variables**:
    Create a `.env` file in this directory and add your API key:
    ```env
    GEMINI_API_KEY=your_api_key_here
    ```
    *(Note: The `.env` file is ignored by Git to keep your key secure.)*

## Usage

### Desktop Mode
Run the assistant directly:
```bash
python maximus.py
```

### Web Interface
Run the local web server:
```bash
python manage.py runserver
```
Then open [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

## Deployment
This project is configured for local deployment. 
# maximus_desktop_assistant
an ai desktop assistant which is used to help in  simple tasks

