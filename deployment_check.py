import os
import sys
from django.core.management.utils import get_random_secret_key

def check_deployment():
    print("--- Deployment Security Check ---")
    
    # Check .env file
    if not os.path.exists('.env'):
        print("[WARNING] .env file not found!")
    else:
        print("[OK] .env file exists.")

    # Check Environment Variables
    secret_key = os.getenv('DJANGO_SECRET_KEY')
    if not secret_key:
        print("[FAIL] DJANGO_SECRET_KEY not set in environment.")
        print("    Suggestion: Add this to your .env file:")
        print(f"    DJANGO_SECRET_KEY={get_random_secret_key()}")
    else:
        print("[OK] DJANGO_SECRET_KEY found.")

    debug_mode = os.getenv('DJANGO_DEBUG')
    if debug_mode == 'True':
        print("[WARNING] DJANGO_DEBUG is set to True. Ensure this is intentional for local testing.")
    elif debug_mode is None:
         print("[INFO] DJANGO_DEBUG not set, defaulting to True (Configuration specific).")
    else:
        print(f"[OK] DJANGO_DEBUG is set to {debug_mode}")

    print("---------------------------------")

if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
        check_deployment()
    except ImportError:
        print("[FAIL] python-dotenv not installed. Run 'pip install python-dotenv'")
