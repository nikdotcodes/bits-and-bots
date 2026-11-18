import os
import secrets

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me-" + secrets.token_hex(16))
DB_PATH = os.getenv("DB_PATH", "codeclub.db")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

# Supabase configuration (use new API keys format)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # Either publishable or secret key
