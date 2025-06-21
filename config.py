# config.py
import os
from dotenv import load_dotenv

load_dotenv() 

NEWSAPI_ORG_API_KEY = os.getenv("NEWSAPI_ORG_API_KEY", "87de43db6453481c965b10abc58375b6")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyANBOTpHkdlpISgG6BLWuUmoKiB8t6ugJo") # Keep placeholder
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "ICICIPRU")

# Removed STOCKDATA_API_TOKEN and EVENTREGISTRY_API_KEY