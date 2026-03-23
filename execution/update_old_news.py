import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from get_news import fetch_full_content

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

async def get_articles_to_update():
    """본문이 비어있거나 너무 짧은(스니펫만 있는) 기사 목록을 가져옵니다."""
    url = f"{SUPABASE_URL}/rest/v1/news_articles?select=id,source_url,content&order=created_at.desc"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                # 본문 글자 수가 300자 미만인 것들을 수집 대상으로 선정 (스니펫은 보통 100-200자 내외)
                to_update = [item for item in data if not item.get('content') or len(item.get('content', '')) < 300]
                return to_update
            return []

async def update_article_content(session, article_id, content):
    """Supabase의 기사 본문을 업데이트합니다."""
    url = f"{SUPABASE_URL}/rest/v1/news_articles?id=eq.{article_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    payload = {"content": content}
    
    async with session.patch(url, headers=headers, json=payload) as resp:
        return resp.status in [200, 204]

async def main():
    print("🚀 누락된 기사 본문 채우기 작업을 시작합니다...")
    articles = await get_articles_to_update()
    print(f"🔎 대상 기사: {len(articles)}개 발견")
    
    if not articles:
        print("✅ 업데이트할 기사가 없습니다.")
        return

    async with aiohttp.ClientSession() as session:
        for i, a in enumerate(articles):
            url = a['source_url']
            aid = a['id']
            print(f"[{i+1}/{len(articles)}] 처리 중: {url}")
            
            full_content = await fetch_full_content(session, url)
            
            if full_content and len(full_content) > 300:
                success = await update_article_content(session, aid, full_content)
                if success:
                    print(f"  ✅ 업데이트 성공 ({len(full_content)} 자)")
                else:
                    print(f"  ❌ 업데이트 실패 (DB 오류)")
            else:
                print(f"  ⚠️ 본문 추출 실패 또는 내용 부족")
            
            # 사이트 차단 방지를 위한 짧은 휴식
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
