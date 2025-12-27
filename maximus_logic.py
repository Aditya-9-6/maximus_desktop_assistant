# assistant/maximus_logic.py
import os
import sys
import time
import threading
import webbrowser
import json
import datetime
import urllib.parse
import traceback
import requests
import subprocess
import re
from django.conf import settings

# --- Optional Imports ---
try:
    import pywhatkit
except:
    pywhatkit = None

try:
    import wikipedia
except:
    wikipedia = None

try:
    import sympy as sp
except:
    sp = None

try:
    from googletrans import Translator
except ImportError:
    Translator = None

try:
    import pyjokes
except ImportError:
    pyjokes = None

# Gemini Setup
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# --- Configuration ---
DEVICE_NAME = "Maximus"
# Use Django's base dir for storage to avoid path issues

# Google App Engine allows writing only to /tmp
if os.getenv('GAE_ENV', '').startswith('standard'):
    STORAGE_DIR = "/tmp"
else:
    STORAGE_DIR = settings.BASE_DIR

CONTACTS_FILE = os.path.join(STORAGE_DIR, "contacts.json")
TASKS_FILE = os.path.join(STORAGE_DIR, "tasks.json")
MEMORY_FILE = os.path.join(STORAGE_DIR, "memory.json")

# --- Storage Helpers ---
def safe_load_json(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load {path}:", e)
        return default

def safe_save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save {path}:", e)

# --- Core Logic Class ---
class MaximusAssistant:
    def __init__(self):
        self.memory = safe_load_json(MEMORY_FILE, {"facts": {}, "conversations": []})

    def save_memory(self):
        safe_save_json(MEMORY_FILE, self.memory)

    def append_conversation(self, role, text):
        self.memory["conversations"].append({
            "time": datetime.datetime.now().isoformat(),
            "role": role,
            "text": text
        })
        self.memory["conversations"] = self.memory["conversations"][-20:]
        self.save_memory()

    def get_gemini_response(self, prompt):
        if not API_KEY:
            return "AI core offline (Gemini API Key missing)."
        
        # Construct a history-aware prompt
        history_text = ""
        for conv in self.memory["conversations"][-5:]:
            role = "User" if conv['role'] == "user" else "Model"
            history_text += f"{role}: {conv['text']}\n"
        
        full_prompt = f"System: You are {DEVICE_NAME}, a helpful web assistant. Keep responses concise.\n{history_text}User: {prompt}\nModel:"

        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            return f"AI Error: {str(e)}"

    def process_command(self, cmd):
        """
        Processes a text command and returns the response string.
        """
        self.append_conversation("user", cmd)
        original_cmd = cmd
        cmd = cmd.lower().strip()
        response = None

        # --- Basic Commands ---
        if cmd in ("help", "commands"):
            response = "I can help with math, weather, wikipedia, tasks, and general questions."

        # --- Math ---
        elif "calculate" in cmd or "solve" in cmd:
            response = self.handle_math(cmd)

        # --- Weather ---
        elif "weather" in cmd:
            loc = cmd.replace("weather", "").replace("in", "").strip()
            response = self.get_weather(loc)

        # --- Wikipedia ---
        elif "wikipedia" in cmd or "search for" in cmd:
            topic = cmd.replace("wikipedia", "").replace("search for", "").strip()
            response = self.wiki_summary(topic)

        # --- YouTube ---
        elif "youtube" in cmd:
            query = cmd.replace("youtube", "").replace("play", "").strip()
            # In a web context, we return the link or open it on server (if local)
            # For web app, returning a link is better, but we'll stick to logic
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            try:
                webbrowser.open_new_tab(url)
            except:
                pass # Browser operations fail on server
            response = f"Opened YouTube search for {query}."

        # --- Tasks ---
        elif "add todo" in cmd or "add task" in cmd:
            task = cmd.replace("add todo", "").replace("add task", "").strip()
            response = self.add_task(task)
        elif "list tasks" in cmd or "show todo" in cmd:
            response = self.list_tasks()
        
        # --- Jokes ---
        elif "joke" in cmd:
            response = self.get_joke()

        # --- Fallback to AI ---
        if not response:
            response = self.get_gemini_response(original_cmd)

        self.append_conversation("assistant", response)
        return response

    # --- Handlers ---

    def handle_math(self, cmd):
        if not sp: return "SymPy not installed."
        try:
            # Basic extraction logic
            expr = cmd.replace("calculate", "").replace("solve", "").strip()
            # Very basic eval for demo purposes
            # In production, use sp.sympify with caution
            if "=" in expr:
                # Equation solving logic simplified
                return "Equation solving requires complex parsing not fully ported yet."
            
            # Arithmetic
            res = sp.sympify(expr).evalf()
            return f"The result is {res}"
        except Exception as e:
            return f"Math error: {e}"

    def get_weather(self, location):
        try:
            url = f"https://wttr.in/{urllib.parse.quote(location)}?format=3" if location else "https://wttr.in/?format=3"
            r = requests.get(url, timeout=5)
            return r.text.strip()
        except:
            return "Could not retrieve weather."

    def wiki_summary(self, topic):
        if not wikipedia: return "Wikipedia module missing."
        try:
            return wikipedia.summary(topic, sentences=2)
        except:
            return "Wikipedia search failed."

    def add_task(self, text):
        tasks = safe_load_json(TASKS_FILE, [])
        tasks.append({"id": int(time.time()), "text": text, "done": False})
        safe_save_json(TASKS_FILE, tasks)
        return f"Added task: {text}"

    def list_tasks(self):
        tasks = safe_load_json(TASKS_FILE, [])
        undone = [t for t in tasks if not t['done']]
        if not undone: return "No pending tasks."
        return ". ".join([f"{t['text']}" for t in undone])

    def get_joke(self):
        if pyjokes: return pyjokes.get_joke()
        return "No jokes available."