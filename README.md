# Stock Trading Alpha Report & Registration UI

Automated stock report system selecting Top 10 Relative Volume (RVOL) spikes daily (07:30 KST).

## 🚀 Deployment

### 1. Web (Cloudflare Pages)
- Connect this GitHub repo.
- **Root Directory**: `public/`
- Build command: (leave empty)
- This hosts the premium email registration page.

### 2. Batch Job (GitHub Actions)
The system is automated via `.github/workflows/daily_report.yml`.
**REQUIRED SECRETS** in Settings -> Secrets and variables -> Actions:
- `GOOGLE_API_KEY`: Gemini API Key.
- `SMTP_USER`: Sender Gmail address.
- `SMTP_PASSWORD`: [Gmail App Password](https://myaccount.google.com/apppasswords).
- `SUPABASE_URL`: Supabase Project URL.
- `SUPABASE_KEY`: Supabase API Key (anon/service_role).

### 3. Database (Supabase)
Run the SQL found in `database/supabase_schema.sql` in your Supabase SQL Editor to create the subscribers table.

## 📁 Project Structure
- `public/`: Registration UI (Static).
- `execution/`: Python batch scripts (core logic).
- `database/`: SQL schema and migrations.
- `docs/`: Project documentation and plans.
- `configs/`: Admin hash and model configurations.
- `directives/`: SOP Documentation.
- `main.py`: Main orchestrator.
