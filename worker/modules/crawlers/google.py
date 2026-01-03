import feedparser
import urllib.parse
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

class GoogleCrawler:
    def __init__(self):
        # 구글 뉴스 RSS 기본 URL
        self.base_url = "https://news.google.com/rss/search"

    def _is_recent(self, pub_date_struct, hours=24):
        """
        RSS 날짜(struct_time)를 확인하여 최신인지 판별
        """
        try:
            # feedparser는 날짜를 struct_time이나 문자열로 줌
            # 여기서는 문자열을 파싱하는 게 더 안전함
            if isinstance(pub_date_struct, str):
                pub_date = parsedate_to_datetime(pub_date_struct)
            else:
                # 안전장치: 정보 없으면 패스
                return False

            now = datetime.now(pub_date.tzinfo)
            
            # 미래 시간이면(가끔 발생) 최신으로 간주
            if pub_date > now: return True
            
            # 차이 계산
            diff = now - pub_date
            return diff <= timedelta(hours=hours)

        except Exception as e:
            # 날짜 파싱 실패 시 그냥 포함시킬지 제외할지 결정 (여기선 안전하게 제외)
            return False

    def search(self, keyword, market="KR"):
        """
        [RSS 방식] 구글 뉴스 검색
        - market='KR': 한국어/한국지역
        - market='US': 영어/미국지역
        """
        try:
            print(f"   Running Google RSS: {keyword}")
            
            # 1. URL 파라미터 설정 (언어/지역)
            if market == "US":
                hl = "en-US"
                gl = "US"
                ceid = "US:en"
            else:
                hl = "ko"
                gl = "KR"
                ceid = "KR:ko"

            # 2. 검색어 인코딩 (한글 -> %EB%84%A4...)
            encoded_query = urllib.parse.quote(keyword)
            
            # 3. 최종 URL 완성
            # 예: https://news.google.com/rss/search?q=삼성전자&hl=ko&gl=KR&ceid=KR:ko
            rss_url = f"{self.base_url}?q={encoded_query}&hl={hl}&gl={gl}&ceid={ceid}"
            
            # 4. RSS 다운로드 및 파싱 (feedparser가 알아서 다 해줌)
            feed = feedparser.parse(rss_url)
            
            results = []
            
            # 5. 결과 필터링
            for entry in feed.entries:
                # 제목, 링크, 날짜 추출
                title = entry.title
                link = entry.link
                pub_date_str = entry.published # 'Mon, 03 Jan 2026 ...'
                
                # [시간 필터링] 24시간 이내 (테스트할 땐 넉넉하게)
                if not self._is_recent(pub_date_str, hours=24):
                    continue
                
                # 구글 뉴스는 본문(summary)이 HTML 덩어리라 지저분함.
                # 대신 제목에 핵심이 다 있으므로 제목 위주로 수집.
                # 필요하면 entry.summary를 clean_html 해서 쓸 수 있음.
                
                results.append(f"[구글] {title}\n(링크: {link})")
                
                # 3개만 모으면 퇴근
                if len(results) >= 3:
                    break
            
            print(f"   ✅ Google RSS 검색으로 {len(results)}개 확보")
            return results

        except Exception as e:
            print(f"❌ Google RSS Error: {e}")
            return []