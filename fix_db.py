import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

headers = {
    "apikey": supabase_key,
    "Authorization": f"Bearer {supabase_key}",
    "Content-Type": "application/json"
}

def fix_table(table_name, time_col):
    url = f"{supabase_url}/rest/v1/{table_name}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to fetch {table_name}:", resp.text)
        return
        
    data = resp.json()
    count = 0
    for row in data:
        # Example timestamp: '2026-03-21T00:13:05.140894+00:00'
        # If it's physically created today but shifted forward by 9 hours because of our previous naive datetime.now().
        # We know any time > '2026-03-20T16:00' was probably inserted incorrectly.
        val = row.get(time_col)
        if val and '2026-03-21T00:' in val:
            # Parse it manually (Python 3.9 handles isoformat including +00:00 sometimes, but let's be careful)
            # Remove +00:00 to parse natively
            clean_val = val.split('+')[0]
            if '.' in clean_val:
                dt = datetime.strptime(clean_val, "%Y-%m-%dT%H:%M:%S.%f")
            else:
                dt = datetime.strptime(clean_val, "%Y-%m-%dT%H:%M:%S")
            
            # Subtract 9 hours to put it in proper UTC
            corrected_dt = dt - timedelta(hours=9)
            # Add back UTC offset so it writes properly to DB
            new_val = corrected_dt.isoformat() + "+00:00"
            
            patch_url = f"{supabase_url}/rest/v1/{table_name}?id=eq.{row['id']}"
            r = requests.patch(patch_url, headers=headers, json={time_col: new_val})
            if r.status_code in [200, 204]:
                count += 1
            else:
                print("Failed to patch:", r.text)
    print(f"Fixed {count} rows in {table_name}.")

if __name__ == '__main__':
    fix_table('batch_summary', 'last_run_at')
    fix_table('execution_logs', 'created_at')
