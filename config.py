import os
from dotenv import load_dotenv

load_dotenv()

# Bot Token (BotFather se milega)
BOT_TOKEN = os.getenv("BOT_TOKEN", "9014327151:AAHzrXEqqF9HY6CDmpdwnuz3N3qsYt-r1Qw")

# FamGateway API Key (Admin panel se bhi change kar sakte hain)
FAM_API_KEY = os.getenv("FAM_API_KEY", "fam_77567c5053f8e96c08aab9f1d5670d4e0df13a5c")

# Firebase Initial URL (Default)
DEFAULT_FIREBASE_URL = os.getenv("FIREBASE_URL", "https://tumhara-baap-default-rtdb.firebaseio.com")

# FamGateway API Endpoint
FAM_API_URL = "https://api.famgateway.in"