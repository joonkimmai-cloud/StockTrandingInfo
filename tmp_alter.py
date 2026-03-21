import os
import requests
from dotenv import load_dotenv

load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
headers = {
    "apikey": supabase_key,
    "Authorization": f"Bearer {supabase_key}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# Supabase REST API does not support arbitrary SQL execution directly via POST /rest/v1.
# Usually we use the RPC endpoint if a function exists. If not, we can't easily run ALTER TABLE.
