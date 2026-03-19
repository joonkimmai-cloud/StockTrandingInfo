import bcrypt
import os
from dotenv import load_dotenv
import requests

load_dotenv()

def create_admin():
    email = "joonkimm.ai@gmail.com"
    password = "dhei@d)(djw$(diow!)"
    
    # 1. Hash Password
    # bcrypt automatically generates a salt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    print(f"[*] Generated hash for {email}")
    print(f"[*] Hash: {hashed_password}")

    # 2. Insert into Supabase (if tables exist)
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("[!] Supabase credentials not found. Print SQL instead.")
    
    sql_insert = f"INSERT INTO admin_users (email, password_hash) VALUES ('{email}', '{hashed_password}');"
    
    print("\n" + "="*50)
    print(" SQL TO RUN IN SUPABASE SQL EDITOR ")
    print("="*50)
    print("""
CREATE TABLE IF NOT EXISTS admin_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);
    """)
    print(sql_insert)
    print("="*50)

if __name__ == "__main__":
    create_admin()
