import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("PIPEDRIVE_API_TOKEN")
DOMAIN = os.getenv("PIPEDRIVE_DOMAIN", "api.pipedrive.com")
BASE_URL_V1 = f"https://{DOMAIN}/api/v1"
BASE_URL_V2 = f"https://{DOMAIN}/api/v2"
