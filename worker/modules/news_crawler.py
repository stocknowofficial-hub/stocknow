import requests
import re
from common.config import settings

class NewsCrawler:
    def __init__(self):
        self.base_url = "https://openapi.naver.com/v1/search/news.json"
        self.headers = {
            "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET
        }

    def clean_html(self, text):
        """네이버 API가 주는 <b>태그나 특수문자 제거"""
        text = re.sub(r'<.*?>', '', text) # 태그 제거
        text = text.replace('&quot;', '"').replace('&apos;', "'").replace('&amp;', '&')
        return text

    def search_news(self, keyword, display=3):
        """
        키워드로 최신 뉴스 검색
        :param keyword: 검색할 단어 (예: '삼성전자', '제주반도체 특징주')
        :param display: 가져올 기사 개수 (기본 3개)
        """
        try:
            # 검색 정확도를 위해 '특징주'라는 단어를 붙여서 검색하면 더 잘 나옵니다.
            # 예: "삼성전자" -> "삼성전자 특징주"
            # 하지만 VI가 아닐 수도 있으니 일단 종목명으로만 검색하거나, 상황 봐서 조정.
            query = f"{keyword}" 
            
            params = {
                "query": query,
                "display": display,
                "sort": "date" # 최신순 (sim: 정확도순) - 급등 이유는 최신순이 좋음
            }

            res = requests.get(self.base_url, headers=self.headers, params=params)
            
            if res.status_code == 200:
                items = res.json().get('items', [])
                news_list = []
                
                for item in items:
                    title = self.clean_html(item['title'])
                    desc = self.clean_html(item['description'])
                    link = item['originallink'] or item['link']
                    
                    news_list.append({
                        "title": title,
                        "desc": desc,
                        "link": link
                    })
                
                return news_list
            else:
                print(f"⚠️ 네이버 검색 에러: {res.status_code}")
                return []

        except Exception as e:
            print(f"❌ 뉴스 크롤링 실패: {e}")
            return []

# 테스트용 (이 파일 직접 실행 시 동작)
if __name__ == "__main__":
    crawler = NewsCrawler()
    # 테스트: 삼성전자 뉴스를 검색해봄
    results = crawler.search_news("삼성전자")
    for i, news in enumerate(results):
        print(f"[{i+1}] {news['title']}")
        print(f"   - {news['desc'][:50]}...")