import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from common.config import settings

class NaverCrawler:
    def __init__(self):
        self.base_url = "https://openapi.naver.com/v1/search/news.json"
        self.headers = {
            "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET
        }

    def _clean_html(self, text):
        text = re.sub(r'<.*?>', '', text)
        text = text.replace('&quot;', '"').replace('&apos;', "'").replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return text

    def _is_recent(self, pub_date_str, hours=24):
        try:
            pub_date = parsedate_to_datetime(pub_date_str)
            now = datetime.now(pub_date.tzinfo)
            # 미래 날짜인 경우(가끔 있음) 보정
            if pub_date > now: return True 
            return (now - pub_date) <= timedelta(hours=hours)
        except:
            return False

    def _fetch_body(self, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=2)
            if response.status_code != 200: return ""
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if "news.naver.com" in url:
                content = soup.select_one("#dic_area")
                return self._clean_html(content.get_text(strip=True)) if content else ""
            
            paragraphs = soup.find_all('p')
            full_text = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            return full_text[:1500]
        except:
            return ""

    def search(self, keyword, display=20): # 검색 개수 늘림 (필터링 대비)
        """
        [고도화된 검색 로직]
        1. 여러 검색어 시도 (특징주 -> 주가 -> 그냥 키워드)
        2. 제목 필터링 (제목에 키워드가 없으면 가차없이 버림)
        """
        
        # 1. 검색어 전략 리스트
        queries = [
            f"{keyword} 특징주", # 1순위: 가장 정확함
            f"{keyword} 주가",   # 2순위: 일반적인 주가 뉴스
            f"{keyword}"         # 3순위: 최후의 수단
        ]

        try:
            for query in queries:
                print(f"   Running Naver Crawler: '{query}'")
                params = {"query": query, "display": display, "sort": "date"}
                res = requests.get(self.base_url, headers=self.headers, params=params, timeout=3)
                
                if res.status_code != 200: continue
                
                items = res.json().get('items', [])
                valid_results = []
                
                for item in items:
                    # [필터링 1] 날짜 확인 (24시간 이내)
                    if not self._is_recent(item['pubDate'], hours=24):
                        continue

                    title = self._clean_html(item['title'])
                    
                    # ⭐️ [필터링 2 - 핵심] 제목에 '종목명'이 포함되어 있는가?
                    # "네이버"를 찾는데 "형지엘리트" 기사가 나오면 버림.
                    if keyword not in title:
                        continue

                    link = item['originallink'] or item['link']
                    desc = self._clean_html(item['description'])
                    
                    # 본문 크롤링 (상위 3개만)
                    content = desc
                    if len(valid_results) < 3:
                        body = self._fetch_body(link)
                        if len(body) > 50: content = body
                    
                    valid_results.append(f"[네이버] {title}\n{content}\n(링크: {link})")
                    
                    # 유효한 기사 3개 찾았으면 루프 종료
                    if len(valid_results) >= 3:
                        break
                
                # 하나라도 유효한 기사를 찾았다면, 더 이상 다음 쿼리(주가, 키워드 등)를 시도하지 않고 리턴
                if valid_results:
                    print(f"   ✅ '{query}' 검색으로 {len(valid_results)}개 유효 기사 확보")
                    return valid_results
            
            # 모든 쿼리를 돌았는데도 없으면 빈 리스트
            print(f"   ❌ '{keyword}' 관련 유효 기사 0건 (제목 필터링 됨)")
            return []

        except Exception as e:
            print(f"❌ Naver Error: {e}")
            return []