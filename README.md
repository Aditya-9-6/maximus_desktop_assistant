# Maximus AI Assistant

Maximus is a powerful, voice-activated desktop assistant powered by Google's Gemini API (Gemini 2.0 Flash). It can perform various tasks such as answering questions include math, playing YouTube videos, checking weather, and more.

## Features
- **AI-Powered**: Uses Google Gemini 2.0 for intelligent conversation.
- **Voice Interaction**: Speaks responses and listens for commands.
- **Web Interface**: Includes a local web chat interface (Django).
- **Tools**: Math solving, Weather, Wikipedia, YouTube, WhatsApp, File management.

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
