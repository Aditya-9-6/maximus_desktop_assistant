# maximus.py - Complete AI Desktop Assistant
"""
Maximus 5.3 - Hackathon Pro (Complete Code)
Features:
- Voice assistant (pyttsx3 TTS + SpeechRecognition)
- NEW: Text input mode (for keyboard use)
- Auto language detect + translate (googletrans + langdetect) [requires internet]
- Math solving, symbolic derivatives/integrals/solve (sympy)
- Weather (wttr.in/Open-Meteo via HTTP, no key) [requires internet]
- YouTube play (pywhatkit.playonyt) [requires internet]
- Gmail unread (optional; needs credentials.json)
- WhatsApp send (pywhatkit) - uses web.whatsapp scheduling
- Wikipedia search
- Maps navigation (open in browser)
- To-dos, alarms, reminders (FIXED: Time parsing issue resolved)
- File & system controls (create/open/delete files, open apps)
- Memory mode (local JSON) to remember small facts
- Fun jokes/facts (pyjokes / useless facts)
- Optional OCR (pytesseract) if Tesseract installed
- Robust error handling & help command
- ChatGPT-powered witty responses
- Wake word listener
- ALL OUTPUTS ARE NOW SPOKEN.
"""

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
import re # Added for robust time/number extraction

# --- Try required and optional imports ---
try:
    import pyttsx3
except Exception as e:
    print("FATAL: pyttsx3 not installed or failing. Install pip package pyttsx3.", e)
    sys.exit(1)

try:
    import speech_recognition as sr
except:
    print("FATAL: speech_recognition required. pip install SpeechRecognition")
    sys.exit(1)


# Optional imports
try:
    import pywhatkit
except:
    pywhatkit = None

try:
    import wikipedia
except:
    wikipedia = None

try:
    import geocoder
except:
    geocoder = None

try:
    import dateparser
except:
    dateparser = None

try:
    import sympy as sp
    from sympy.parsing.mathematica import parse_mathematica # For robust parsing
except:
    sp = None
    print("Warning: SymPy is not available. Math features will be limited.")

try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    import pickle
except:
    build = None
    InstalledAppFlow = None
    pickle = None

# translation & detection
try:
    from langdetect import detect
except ImportError:
    detect = None
try:
    from googletrans import Translator
except ImportError:
    Translator = None

# optional niceties
try:
    import pyjokes
except ImportError:
    pyjokes = None

# optional OCR
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except:
    OCR_AVAILABLE = False
    print("Warning: OCR (pytesseract/Pillow) is not available. Install pytesseract and the Tesseract executable.")

# ---------------- CONFIG ----------------
DEVICE_NAME = "Maximus"
CONTACTS_FILE = "contacts.json"
TASKS_FILE = "tasks.json"
MEMORY_FILE = "memory.json"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
GMAIL_TOKEN = "token.pickle"
WAKE_WORD = DEVICE_NAME.lower()

# --- Gemini Configuration ---
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load variables from your .env file
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    print("[SUCCESS] Gemini API key loaded successfully.")
else:
    print("[WARNING] GEMINI_API_KEY not found in .env file. Smart responses will be disabled.")

# ---------------- TTS ----------------
engine = pyttsx3.init()
engine.setProperty('rate', 165)
voices = engine.getProperty('voices')
try:
    # Try setting to a male or female voice, or default to the first one
    # Note: Voice index may vary per system.
    engine.setProperty('voice', voices[0].id) 
except:
    pass

def speak(text):
    """Speak and print (centralized so we can change voice engine later)"""
    # Ensure text is converted to string for pyttsx3
    text = str(text) 
    print(f"[{DEVICE_NAME}] {text}")
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("TTS error:", e)

# ---------------- Speech Recognition ----------------
recognizer = sr.Recognizer()

def listen_once(timeout=None, phrase_time_limit=None):
    """Record once from microphone and return recognized text (lowercased)."""
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("Listening...")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except Exception as ex:
            print("Recording error:", ex)
            return ""
    try:
        text = recognizer.recognize_google(audio).lower()
        print("Heard:", text)
        return text
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print("Speech recognition error:", e)
        return ""

def get_command_input():
    """Provides a menu to choose between voice and text input."""
    print("\n--- Input Mode Selection ---")
    print("1. Voice Command (Say 'Maximus' to start)")
    print("2. Text Command (Type your command)")
    print("3. Quit")
    
    choice = input("Enter 1, 2, or 3: ").strip()
    
    if choice == '1':
        return 'VOICE_MODE'
    elif choice == '2':
        # Get command directly from keyboard
        command = input(f"[{DEVICE_NAME} Text Mode] Enter Command: ").strip()
        return command
    elif choice == '3':
        return 'SLEEP_MODE'
    else:
        speak("Invalid choice. Please try again.")
        return get_command_input() # Loop until valid input

# ---------------- Storage Helpers ----------------
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

# ---------------- Contacts / Memory ----------------
def load_contacts():
    return safe_load_json(CONTACTS_FILE, {})

def load_memory():
    return safe_load_json(MEMORY_FILE, {"facts": {}, "conversations": []})

def remember_fact(key, value):
    mem = load_memory()
    mem["facts"][key] = value
    safe_save_json(MEMORY_FILE, mem)
    speak(f"Saved: {key} equals {value}")

def recall_fact(key):
    mem = load_memory()
    return mem["facts"].get(key)

def append_conversation(role, text):
    mem = load_memory()
    # Ensure text is clean and not the "SLEEP_MODE" signal
    if text != "SLEEP_MODE":
        mem["conversations"].append({"time": datetime.datetime.now().isoformat(), "role": role, "text": text})
        # cap conversation history to last 20 lines
        mem["conversations"] = mem["conversations"][-20:]
        safe_save_json(MEMORY_FILE, mem)

# ---------------- AI/Gemini ----------------
def get_gemini_response(prompt, memory):
    """Gets an intelligent, context-aware response from the Gemini API."""
    if not api_key:
        return "The AI core is offline. Please install and configure the Gemini API key."

    # Build the message history for context
    history_text = ""
    # Add recent conversation history from memory
    for conv in memory["conversations"][-5:]: # Use last 5 lines for short-term memory
        role = "User" if conv['role'] == "user" else "Model"
        history_text += f"{role}: {conv['text']}\n"
    
    # Add the current user prompt
    full_prompt = f"System: You are a witty, helpful, and powerful desktop AI assistant named {DEVICE_NAME}. Keep responses concise and engaging. Only answer if the command cannot be handled by a specific tool.\n{history_text}User: {prompt}\nModel:"

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(full_prompt)
        text = response.text.strip()
        return text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "I apologize, but my connection to the AI matrix is experiencing turbulence."

# ---------------- Translation ----------------
translator = Translator() if Translator else None

def detect_language(text):
    if not detect:
        return None
    try:
        return detect(text)
    except:
        return None

def translate_to_english(text):
    if not translator:
        return text
    try:
        res = translator.translate(text, dest='en')
        return res.text
    except Exception as e:
        print("Translate error:", e)
        return text

# ---------------- Math (SymPy + mathjs fallback) ----------------
def safe_sympy_expr(expr_str):
    """Try to parse the expression into sympy-friendly string, handling common voice errors."""
    expr_str = expr_str.replace('^', '').replace('×', '*').replace('÷', '/')
    expr_str = expr_str.replace('power of', '').replace('to the power', '')
    return expr_str

def compute_derivative(expr_str):
    if not sp: return "SymPy not available. Cannot compute derivatives."
    try:
        x = sp.Symbol('x')
        # Use a more robust parser for voice input that may include 'x' or 'variable'
        match = re.search(r'of\s*(.+)', expr_str, re.IGNORECASE)
        if match:
             expr_str = match.group(1).strip()
             
        # Simplify the expression before passing to sympify
        expr = sp.sympify(safe_sympy_expr(expr_str))
        d = sp.diff(expr, x)
        return f"The derivative of {expr_str} with respect to x is {d}."
    except Exception as e:
        print("Derivative error:", e)
        return "I had trouble computing that derivative. Ensure your expression is valid."

def compute_integral(expr_str):
    if not sp: return "SymPy not available. Cannot compute integrals."
    try:
        x = sp.Symbol('x')
        match = re.search(r'of\s*(.+)', expr_str, re.IGNORECASE)
        if match:
             expr_str = match.group(1).strip()
             
        expr = sp.sympify(safe_sympy_expr(expr_str))
        I = sp.integrate(expr, x)
        return f"The indefinite integral is {I} plus C."
    except Exception as e:
        print("Integral error:", e)
        return "I couldn't compute that integral."

def solve_equation(eq_str):
    if not sp: return "SymPy not available. Cannot solve equations."
    try:
        # Tidy up the equation string before parsing
        eq = eq_str.split("solve", 1)[-1].strip()
        eq = safe_sympy_expr(eq)
        
        # Determine the variable to solve for (default to x)
        x = sp.Symbol('x')
        var_match = re.search(r'for\s+([a-zA-Z])', eq_str, re.IGNORECASE)
        if var_match:
            var = sp.Symbol(var_match.group(1))
        else:
            var = x

        if '=' in eq:
            left, right = eq.split('=',1)
            sol = sp.solve(sp.Eq(sp.sympify(left), sp.sympify(right)), var)
        else:
            # Assume solving for equation = 0
            sol = sp.solve(sp.sympify(eq), var)
            
        if sol:
            return f"The solutions for {var} are: {sol}"
        else:
            return "The equation has no simple solutions, or I could not find them."
    except Exception as e:
        print("Solve error:", e)
        return "I couldn't solve that equation. Please check the format."

def evaluate_arithmetic(expr_str):
    if sp:
        try:
            # Pre-replace common voice transcription errors like 'x' for 'times'
            expr_str = expr_str.replace("times", "*").replace("minus", "-").replace("plus", "+").replace("divided by", "/")
            expr_str = safe_sympy_expr(expr_str)
            
            # Simple check for variables, if present, use AI fallback
            if any(c.isalpha() for c in expr_str.replace('pi', '').replace('e', '')):
                 raise ValueError("Expression contains variables, falling back to AI/solver.")
                 
            val = sp.sympify(expr_str).evalf(chop=True) # chop=True for small error
            return f"The result is approximately: {val}"
        except Exception as e:
            # Fallback for complex arithmetic or if SymPy fails
            print("SymPy arithmetic failed, attempting mathjs/AI fallback:", e)
            pass
            
    # fallback to mathjs public API for robust arithmetic
    try:
        url = "https://api.mathjs.org/v4/"
        # Re-parse for mathjs API compatibility (uses ** for power, which is fine)
        expr_str = expr_str.replace('^', '').replace('×', '*').replace('÷', '/')
        resp = requests.post(url, json={"expr": expr_str}, timeout=8)
        if resp.status_code == 200:
            result = resp.text.strip()
            # Mathjs returns "invalid expression" on failure
            if "invalid expression" in result:
                return "Could not evaluate expression. Please check the math syntax."
            return f"The result is: {result}"
    except Exception as e:
        print("mathjs fallback error:", e)
    return "I could not evaluate that mathematical expression."

# ---------------- Weather (wttr.in) ----------------
def get_weather_simple(location_text=""):
    try:
        if location_text:
            url = f"https://wttr.in/{urllib.parse.quote(location_text)}?format=3"
        else:
            url = "https://wttr.in/?format=3"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            return r.text.strip()
    except Exception as e:
        print("Weather error:", e)
    return "I could not retrieve weather data at this time."

# ---------------- Wikipedia ----------------
def wiki_summary(topic):
    if not wikipedia:
        return "Wikipedia module not installed."
    try:
        # Auto-correct the topic name (like voice does)
        topic = topic.replace("what is", "").replace("who is", "").strip()
        return wikipedia.summary(topic, sentences=2)
    except Exception as e:
        print("Wikipedia error:", e)
        return f"Couldn't find Wikipedia info for {topic}."

# ---------------- YouTube / Spotify / Maps ----------------
def play_youtube(query):
    if pywhatkit:
        try:
            pywhatkit.playonyt(query)
            return f"Playing {query} on YouTube. Check your browser now."
        except Exception as e:
            print("YouTube play error:", e)
    # fallback
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    webbrowser.open_new_tab(url)
    return f"Opened YouTube search for {query} in your browser."

def open_maps(destination):
    # Use Google Maps standard URL format
    url = f"https://www.google.com/maps/dir/?api=1&destination={urllib.parse.quote(destination)}"
    webbrowser.open_new_tab(url)
    return f"Opened Google Maps for directions to {destination}."

# ---------------- WhatsApp ----------------
def send_whatsapp_by_number(number, message):
    if not pywhatkit:
        return "pywhatkit not installed."
    try:
        # Clean the number to ensure only digits and '+' remain
        number = re.sub(r'[^0-9+]', '', number)
        if not number.startswith('+'):
            return "Please ensure the phone number includes the country code, starting with plus sign, like +1234567890."
            
        now = datetime.datetime.now()
        target_hour = now.hour
        # Schedule 1 minute later
        target_min = (now.minute + 1) % 60
        pywhatkit.sendwhatmsg(number, message, target_hour, target_min, wait_time=15, tab_close=True)
        return f"WhatsApp message scheduled for {target_hour:02}:{target_min:02}. Your browser will open shortly."
    except Exception as e:
        print("WhatsApp error:", e)
        return "Failed to schedule WhatsApp message."

# ---------------- Gmail ----------------
# [Gmail functions remain unchanged, assuming proper installation and configuration]
def get_gmail_service():
    if not (InstalledAppFlow and build and pickle):
        raise RuntimeError("Gmail libs not available.")
    creds = None
    if os.path.exists(GMAIL_TOKEN):
        with open(GMAIL_TOKEN, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not getattr(creds, 'valid', False):
        if not os.path.exists('credentials.json'):
            raise RuntimeError("credentials.json not found for Gmail OAuth.")
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open(GMAIL_TOKEN, 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service

def read_unread_emails(service, max_count=3):
    try:
        res = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
        messages = res.get('messages', [])
        if not messages:
            return "No unread emails."
        out = [f"You have {len(messages)} unread emails. Here are the top {min(len(messages), max_count)}:"]
        for msg in messages[:max_count]:
            m = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
            headers = m.get('payload', {}).get('headers', [])
            sender = next((h['value'] for h in headers if h['name'] == "From"), "Unknown")
            subject = next((h['value'] for h in headers if h['name'] == "Subject"), "(No Subject)")
            out.append(f"From {sender}. Subject: {subject}")
        # Convert list of strings to a single string for speaking
        return ". ".join(out)
    except Exception as e:
        print("Gmail read error:", e)
        return "Failed to read Gmail. Check your credentials and token file."


# ---------------- To-dos ----------------
# [To-do functions remain unchanged]
def load_tasks(): return safe_load_json(TASKS_FILE, [])
def save_tasks(tasks): safe_save_json(TASKS_FILE, tasks)

def add_task(text):
    tasks = load_tasks()
    tasks.append({"id": int(time.time()*1000), "text": text, "done": False})
    save_tasks(tasks)
    return f"Added task: {text}"

def list_tasks():
    tasks = load_tasks()
    undone = [t for t in tasks if not t.get("done")]
    if not undone:
        return "You have no outstanding tasks."
    out = [f"You have {len(undone)} tasks remaining:"]
    for t in undone:
        # Use a shorter ID for speaking/reading
        short_id = str(t['id'])[-4:]
        out.append(f"ID {short_id}: {t['text']}")
    # Convert list of strings to a single string for speaking
    return ". ".join(out)

def mark_task_done(task_id_part):
    tasks = load_tasks()
    found = False
    for t in tasks:
        # Match against the full ID or the last 4 digits (easier for voice)
        if str(t['id']).endswith(str(task_id_part)):
            t['done'] = True
            found = True
            break
    if found:
        save_tasks(tasks)
        return f"Marked task ending in {task_id_part} as done."
    return f"Task ID ending in {task_id_part} not found."

# ---------------- Alarms / Reminders (FIXED) ----------------
def set_alarm(hm, label="Alarm"):
    """Sets an alarm for a specific HH:MM time."""
    try:
        # Extract time in HH:MM format using regex for robustness
        time_match = re.search(r'(\d{1,2})[:](\d{2})', hm)
        if not time_match:
            return "Couldn't parse alarm time. Use HH:MM format, like 07:30."
            
        h, m = map(int, time_match.groups())
        
        target_time = datetime.time(h, m)
        now = datetime.datetime.now()
        run = datetime.datetime.combine(now.date(), target_time)
        
        # If the target time is in the past today, set it for tomorrow
        if run < now:
            run += datetime.timedelta(days=1)
            
        delay = (run - now).total_seconds()
        
        # Ensure delay is positive
        if delay <= 0:
             return "Alarm time is in the immediate past. Try a few minutes later."
             
        t = threading.Timer(delay, lambda: speak(f"Time's up! {label}! It's {target_time.strftime('%I:%M %p')} now."))
        t.daemon = True
        t.start()
        return f"Alarm set successfully for {target_time.strftime('%I:%M %p')}."
    except Exception as e:
        print("Alarm parse error:", e)
        return "I had trouble setting that alarm. Make sure the time is correct."

def set_reminder(text):
    """Sets a reminder using natural language time parsing."""
    if not dateparser:
        return "dateparser module missing. Cannot set reminders."
    
    # Use dateparser to find the time/date component
    dt = dateparser.parse(text, settings={'PREFER_DATES_FROM':'future', 'RELATIVE_BASE': datetime.datetime.now()})
    
    if not dt:
        return "Couldn't understand reminder time. Try 'in 10 minutes' or 'tomorrow at 8 a.m.'."
    
    delay = (dt - datetime.datetime.now()).total_seconds()
    
    if delay <= 10: # 10 seconds buffer
        return "That time is either in the past or too soon."
    
    # Remove the time-related phrase from the text to get the reminder message
    # This is a bit tricky, but we can assume the reminder is everything after the main verb
    reminder_text = text.split('remind me to', 1)[-1].split('remind me', 1)[-1].strip()
    
    # If the text is just the time phrase, default to a generic reminder
    if not reminder_text or any(word in reminder_text.lower() for word in ['in', 'at', 'tomorrow', 'next']):
        # If time parsing was successful but the message is still time-focused, 
        # try to strip the time from the message for a cleaner reminder.
        reminder_text = "Check your schedule"
    
    t = threading.Timer(delay, lambda: speak(f"Reminder! The time is {dt.strftime('%I:%M %p')}. You asked me to remind you to: {reminder_text}"))
    t.daemon = True
    t.start()
    return f"Reminder set for {dt.strftime('%Y-%m-%d at %I:%M %p')} for: {reminder_text}"

# ---------------- File & System Controls ----------------
# [File/System functions remain largely unchanged]
def create_file(filename, content=""):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Created file {filename}."
    except Exception as e:
        print("Create file error:", e)
        return "Failed to create file."

def open_file(filename):
    try:
        if os.path.exists(filename):
            webbrowser.open_new_tab(f"file://{os.path.abspath(filename)}")
            return f"Opened {filename}."
        return "File not found."
    except Exception as e:
        print("Open file error:", e)
        return "Failed to open file."

def delete_file(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
            return f"Deleted {filename}."
        return "File not found."
    except Exception as e:
        print("Delete file error:", e)
        return "Failed to delete file."

def run_system_command(cmd):
    # This is a potentially dangerous function and should be used cautiously.
    try:
        subprocess.Popen(cmd, shell=True)
        return f"Executing {cmd}."
    except Exception as e:
        print("Run system command error:", e)
        return "Failed to execute command."

def take_screenshot(save_to="screenshot.png"):
    # [Platform specific screenshot logic remains]
    try:
        if sys.platform.startswith('linux'):
            # This is non-standard but often works with 'scrot'
            os.system(f"scrot {save_to}") 
        elif sys.platform.startswith('darwin'):
            os.system(f"screencapture {save_to}")
        elif sys.platform.startswith('win'):
            # A simple message that requires external libs for robust Windows functionality
            return "Windows screenshot is not directly supported without additional libraries like 'pyscreenshot' or 'Pillow'."
        else:
            return "Screenshot not supported on this platform."
        return f"Screenshot saved to {save_to} in the current directory."
    except Exception as e:
        print("Screenshot error:", e)
        return "Failed to take screenshot."

# ---------------- OCR ----------------
# [OCR functions remain unchanged]
def ocr_image(path):
    if not OCR_AVAILABLE:
        return "OCR not available (pytesseract or pillow missing)."
    if not os.path.exists(path):
        return "Image not found."
    try:
        text = pytesseract.image_to_string(Image.open(path))
        return "Text detected: " + (text.strip() or "No text detected.")
    except Exception as e:
        print("OCR error:", e)
        return "OCR failed."

# ---------------- Fun stuff ----------------
def random_joke():
    """FIXED: Now returns the text for speaking."""
    if pyjokes:
        try:
            return pyjokes.get_joke()
        except:
            pass
    # fallback to online useless facts
    try:
        r = requests.get("https://uselessfacts.jsph.pl/random.json?language=en", timeout=6).json()
        return r.get("text", "Here's a fun fact for you.")
    except:
        return "I tried to be funny but failed. Sorry."

# ---------------- Fallback / Help ----------------
def fallback_response(cmd):
    if "how are you" in cmd:
        return "Tesla-level charged and ready."
    if "hello" in cmd or "hi" in cmd:
        return "Hey! Maximus at your service. How can I assist?"
    return "I didn't catch that. Say 'help' to hear what I can do."

def help_text():
    return (
        "I can do a lot. Try commands like: "
        "- 'play <song>' (YouTube), "
        "- 'search <topic>' (Wikipedia), "
        "- 'weather in <city>', "
        "- 'calculate 5 plus 3' or 'solve x squared equals 9', "
        "- 'derivative of x squared', "
        "- 'add todo <task>' / 'show todo' / 'mark task <id> done', "
        "- 'set alarm for 07:30' / 'remind me <time phrase>', "
        "- 'send whatsapp' (will prompt for number/message), "
        "- 'create file <name>' / 'delete file <name>', "
        "- 'remember <key> is <value>' and 'what is <key>', "
        "- 'check email' (Gmail must be configured), "
        "- 'tell me a joke', "
        "- 'sleep' to return to wake word mode, or 'quit' to exit the program."
    )

# ---------------- Command Dispatcher ----------------
def process_command(cmd, contacts, gmail_service):
    """Parses and executes a single command string."""
    mem = load_memory() 
    append_conversation("user", cmd)
    original = cmd
    cmd = cmd.lower().strip()
    response = None

    # --- IMMEDIATE SYSTEM COMMANDS ---
    # 'quit' will exit the program entirely, 'sleep' returns to wake word mode
    if cmd in ("exit", "quit", "shutdown"):
        speak("Goodbye. Shutting down all systems.")
        sys.exit(0) # Exit the entire program

    if cmd in ("sleep", "go to sleep", "stop listening"):
        return "SLEEP_MODE" # Signal to the main loop to go back to wake word listener

    if cmd in ("help", "what can you do", "commands"):
        response = help_text()
    
    # --- TRANSLATION: Auto-detect and translate if not English ---
    try:
        lang = detect_language(original) if detect else None
        if lang and lang != 'en':
            translated = translate_to_english(original)
            cmd = translated.lower()
            speak(f"Detected language {lang}. Translated: {translated}")
    except Exception as e:
        print("Auto-translate error:", e)


    # --- MEMORY/FACTS ---
    if response is None and cmd.startswith("remember "):
        try:
            rest = cmd.replace("remember ", "", 1).strip()
            if " is " in rest:
                key, val = rest.split(" is ", 1)
            elif " =" in rest:
                key, val = rest.split("=", 1)
            else:
                response = "Use format: remember <key> is <value>."
            if response is None:
                # The remember_fact function already calls speak() and saves the response
                remember_fact(key.strip(), val.strip()) 
                return # Skip final speak, as remember_fact already did it
        except Exception:
            response = "Couldn't remember that."

    elif response is None and (cmd.startswith("what is ") or cmd.startswith("who is ")):
        key = cmd.split(" ", 2)[-1].strip()
        val = recall_fact(key)
        if val:
            response = f"{key} is {val}."
        # fall-through to wiki/AI search if not in memory
        
    # --- MATH & SYMBOLIC ---
    elif response is None and "derivative of" in cmd:
        expr = cmd.split("derivative of", 1)[-1].strip()
        response = compute_derivative(expr)
    elif response is None and ("integrate" in cmd or "integral of" in cmd):
        expr = cmd.split("integrate", 1)[-1].split("integral of", 1)[-1].strip()
        response = compute_integral(expr)
    elif response is None and ("solve equation" in cmd or "solve for" in cmd or "solve" in cmd and '=' in cmd):
        # Extract the equation/expression after 'solve'
        eq = cmd.split("solve", 1)[-1].strip()
        response = solve_equation(eq)
    elif response is None and ("evaluate" in cmd or "calculate" in cmd or ("what is" in cmd or "what's" in cmd) and any(op in cmd for op in ['+', '-', '*', '/', 'mod', 'plus', 'minus', 'times'])):
        # Strip the trigger words to get the expression
        expr = cmd.split("evaluate", 1)[-1].split("calculate", 1)[-1].split("what is", 1)[-1].split("what's", 1)[-1].strip()
        response = evaluate_arithmetic(expr)

    # --- WIKIPEDIA / SEARCH ---
    elif response is None and ("search for" in cmd or "wikipedia" in cmd or "tell me about" in cmd):
        topic = cmd.split("search for", 1)[-1].split("wikipedia", 1)[-1].split("tell me about", 1)[-1].strip()
        response = wiki_summary(topic)
        
    # --- WEATHER ---
    elif response is None and "weather in" in cmd:
        location = cmd.split("weather in", 1)[-1].strip()
        response = get_weather_simple(location)
    elif response is None and cmd == "weather":
        response = get_weather_simple()

    # --- YOUTUBE / MAPS ---
    elif response is None and ("play on youtube" in cmd or "youtube" in cmd and "play" in cmd):
        query = cmd.split("youtube", 1)[-1].split("play", 1)[-1].strip()
        response = play_youtube(query)
    elif response is None and ("open maps" in cmd or "navigate to" in cmd):
        destination = cmd.split("open maps", 1)[-1].split("navigate to", 1)[-1].strip()
        response = open_maps(destination)

    # --- GMAIL ---
    elif response is None and ("check email" in cmd or "unread mail" in cmd):
        try:
            service = get_gmail_service()
            response = read_unread_emails(service)
        except RuntimeError as e:
            response = f"Gmail configuration error: {e}"
        except Exception as e:
            response = f"Gmail failed: {e}"

    # --- WHATSAPP (Interactive) ---
    elif response is None and "send whatsapp" in cmd:
        # Interactive sequence for WhatsApp (only works well in voice/command line mode)
        speak("Who would you like to message? Please say or type the phone number, including the plus sign and country code.")
        number = listen_once(timeout=10, phrase_time_limit=5).strip()
        if not number: 
            return "Cancelled. No number provided."
        speak("What is the message you want to send?")
        message = listen_once(timeout=15, phrase_time_limit=10).strip()
        if not message: 
            return "Cancelled. No message provided."
        response = send_whatsapp_by_number(number, message)

    # --- TO-DOS ---
    elif response is None and ("add todo" in cmd or "add task" in cmd):
        task = cmd.split("add todo", 1)[-1].split("add task", 1)[-1].strip()
        response = add_task(task)
    elif response is None and ("show todo" in cmd or "list tasks" in cmd):
        response = list_tasks()
    elif response is None and ("mark task" in cmd and "done" in cmd):
        try:
            # Regex to find a number or a sequence of characters that look like an ID
            match = re.search(r'task\s*(\d+)\s*done', cmd)
            if match:
                 task_id = match.group(1).strip()
                 response = mark_task_done(task_id)
            else:
                 response = "Couldn't identify the task ID. Say 'mark task 1234 done'."
        except:
            response = "Couldn't identify the task ID. Say 'mark task 1234 done'."

    # --- ALARMS/REMINDERS (FIXED) ---
    elif response is None and "set alarm for" in cmd:
        time_str = cmd.split("set alarm for", 1)[-1].strip()
        response = set_alarm(time_str)
    elif response is None and ("remind me to" in cmd or "remind me" in cmd):
        text = cmd.split("remind me to", 1)[-1].split("remind me", 1)[-1].strip()
        response = set_reminder(text)

    # --- FILES & SYSTEM ---
    elif response is None and "create file" in cmd:
        filename = cmd.split("create file", 1)[-1].strip()
        response = create_file(filename)
    elif response is None and "open file" in cmd:
        filename = cmd.split("open file", 1)[-1].strip()
        response = open_file(filename)
    elif response is None and "delete file" in cmd:
        filename = cmd.split("delete file", 1)[-1].strip()
        response = delete_file(filename)
    elif response is None and "take screenshot" in cmd:
        response = take_screenshot()

    # --- OCR ---
    elif response is None and ("ocr" in cmd or "read text from" in cmd):
        path = cmd.split("ocr", 1)[-1].split("read text from", 1)[-1].strip()
        response = ocr_image(path)

    # --- FUN STUFF (FIXED) ---
    elif response is None and ("joke" in cmd or "fun fact" in cmd):
        response = random_joke() # This now returns the text to be spoken

    # --- FALLBACK / GPT RESPONSE ---
    if response is None:
        # Pass the original command (which might have been auto-translated) to GPT
        response = get_gemini_response(original, mem)
        # If GPT fails, use local fallback
        if response.startswith("I apologize") or response.startswith("The AI core is offline"):
            response = fallback_response(cmd)

    # Final check and conversation append
    if response:
        append_conversation("assistant", response)
        return response
    else:
        # Should be unreachable if fallback is working, but safety check
        return fallback_response(cmd) 

# ---------------- Main Assistant Loop ----------------

def main_loop(contacts, gmail_service, voice_mode=True):
    """The main loop for the desktop assistant, active when a command is expected."""
    
    while True:
        try:
            if voice_mode:
                # Continuous listening for voice command
                command = listen_once(timeout=None, phrase_time_limit=10)
            else:
                # Text input mode
                command = input(f"[{DEVICE_NAME} Text Mode] Enter Command: ").strip()

            if not command:
                continue

            # Process the command
            result = process_command(command, contacts, gmail_service)
            
            if result == "SLEEP_MODE":
                # Only speak this if we were in voice mode. In text mode, we just exit the loop.
                if voice_mode:
                    speak("Acknowledged. Initiating stand-by mode. Say my name to reactivate.")
                return # Exit the main loop to return to the selection menu/wake word listener
            
            # Speak the result (speak() also prints it)
            speak(result)

        except KeyboardInterrupt:
            speak("Program terminated by user.")
            sys.exit(0)
        except Exception as e:
            speak("An unexpected system error occurred.")
            print(f"CRITICAL ERROR: {e}\n{traceback.format_exc()}")
            time.sleep(1) 

# ---------------- Wake Word Listener / Startup ----------------

def wake_word_listener():
    """Initializes the assistant and manages the Voice/Text selection."""
    print(f"\n{DEVICE_NAME} is loading resources...")
    
    # Pre-load resources once
    contacts = load_contacts()
    gmail_service = None
    try:
        # Attempt to initialize Gmail service on startup
        gmail_service = get_gmail_service()
    except Exception as e:
        print(f"Warning: Gmail service failed to initialize. Feature disabled. ({e})")

    speak(f"Systems check complete. I am {DEVICE_NAME}, online and ready.")
    

    # --- Start Menu Loop ---
    while True:
        input_mode_choice = get_command_input()
        
        if input_mode_choice == 'SLEEP_MODE':
            speak("Program exit confirmed. Goodbye.")
            break
        
        elif input_mode_choice == 'VOICE_MODE':
            print(f"\n{DEVICE_NAME} is listening for wake word: '{WAKE_WORD}'...")
            
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                # Loop to listen for the wake word
                while True:
                    try:
                        print(f"[{DEVICE_NAME} Standby]")
                        audio = recognizer.listen(source, phrase_time_limit=3)
                        text = recognizer.recognize_google(audio).lower()
                        
                        if WAKE_WORD in text:
                            print(f"*** Wake word detected: {text} ***")
                            speak("Yes? I'm listening.")
                            main_loop(contacts, gmail_service, voice_mode=True) # Start the voice assistant
                            # Returns here when 'sleep' command is given, re-enters wake word loop
                            break # Exit the wake word inner loop to return to the main selection menu

                    except sr.UnknownValueError:
                        pass  # Keep listening
                    except Exception as e:
                        print(f"Wake word listening error: {e}")
                        time.sleep(1)

        else:
            # Text command was provided directly from the menu
            speak(f"Initiating Text Command: {input_mode_choice}")
            result = process_command(input_mode_choice, contacts, gmail_service)
            if result == "SLEEP_MODE":
                 speak("Text mode finished. Returning to menu.")
            else:
                 speak(result)
        
    # --- End of while True ---

# End of while True ---

if __name__ == "__main__":
    print("Starting wake word listener...")
    try:
        wake_word_listener()  # This is the line that runs right before the exit
    except Exception as e:
        print(f"FATAL ERROR in wake_word_listener: {e}")
        # The line below is a temporary fix for one of your old errors. 
        # If you are still using Python 3.13, you might need it.
        # import traceback; traceback.print_exc() 

print("Program finished.") # This line should only print if the listener completes or crashes.