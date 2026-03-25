import asyncio
import aiohttp
from bs4 import BeautifulSoup

def select_first(element, selectors):
    for s in selectors:
        found = element.select_one(s)
        if found: return found
    return None

async def test():
    stock_name = "Tesla"
    query = f"{stock_name} Finance"
    url = f"https://www.google.com/search?q={query}+stock+news&tbm=nws&tbs=sbd:1"
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            print(f"Status: {response.status}")
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            with open('.tmp/debug_google.html', 'w', encoding='utf-8') as f:
                f.write(html)
            
            items = soup.select('a.WlydOe')
            print(f"Items found with a.WlydOe: {len(items)}")
            
            if not items:
                items = soup.select('div.SoS9Cc, div.v7wZne, div[role="listitem"]')
                print(f"Items found with fallbacks: {len(items)}")

            for i, item in enumerate(items[:3]):
                print(f"--- Item {i} ---")
                title_el = select_first(item, ['div[role="heading"]', 'h3', '.n0jPhd', '.mCBkyc'])
                if title_el:
                    print(f"Title: {title_el.get_text().strip()}")
                else:
                    print("Title NOT FOUND")
                
                link = item.get('href') if item.name == 'a' else (item.select_one('a').get('href') if item.select_one('a') else None)
                print(f"Link: {link}")

if __name__ == "__main__":
    asyncio.run(test())
