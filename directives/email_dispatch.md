# SOP: Email Dispatch System

## Purpose
Distribute the analyzed report to all subscribers via a premium HTML email.

## Process
1. **Template**: Use a responsive HTML/CSS template with clear sections for US/KR markets.
2. **Data**: Inject content from `.tmp/report.json`.
3. **Recipients**:
   - Always include `joonkimm.ai@gmail.com`.
   - Fetch additional emails from Supabase `subscribers` table.
4. **Dispatch**: Use Gmail SMTP with `Retry` logic for failed attempts.
5. **Logging**: Record success/failure for each transmission.
