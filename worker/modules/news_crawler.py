import asyncio
import ujson
import requests
import re
import os
import google.generativeai as genai
from bs4 import BeautifulSoup
import redis.asyncio as redis # [필수] 비동기 Redis 라이브러리
from common.config import settings

# ==============================================================================
# 🎛️ [개발자 제어판]
# ==============================================================================
# 옵션: "GEMINI", "LOCAL", "MOCK", "OFF"
AI_PROVIDER = "LOCAL" 

# [Local LLM 설정]
LOCAL_LLM_URL = "http://127.0.0.1:1234/v1/chat/completions"
# LOCAL_MODEL_NAME = "qwen/qwen3-4b-thinking-2507"
# LOCAL_MODEL_NAME = "qwen/qwen3-4b-2507"
LOCAL_MODEL_NAME = "qwen/qwen3-vl-8b"



class NewsCrawler:
    def __init__(self):
        # 1. 네이버 API 설정
        self.naver_base_url = "https://openapi.naver.com/v1/search/news.json"
        self.naver_headers = {
            "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET
        }

        # 2. Gemini 설정 (모드가 GEMINI일 때만 로드)
        self.gemini_model = None
        if AI_PROVIDER == "GEMINI":
            if settings.GOOGLE_API_KEY:
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                print("✨ [설정] Gemini 1.5 Flash 모드 가동")
            else:
                print("⚠️ [경고] 구글 API 키가 없습니다. MOCK 모드로 전환합니다.")
        
        elif AI_PROVIDER == "LOCAL":
            print(f"🖥️ [설정] Local LLM 모드 가동 (Target: {LOCAL_MODEL_NAME})")
        
        elif AI_PROVIDER == "MOCK":
            print("🛠️ [설정] 개발용 Mock 모드 (비용 0원)")

    # --------------------------------------------------------------------------
    # 🧹 HTML 정제 및 Deep Crawling (동기 함수)
    # --------------------------------------------------------------------------
    def clean_html(self, text):
        text = re.sub(r'<.*?>', '', text)
        text = text.replace('&quot;', '"').replace('&apos;', "'").replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return text

    def fetch_article_body(self, url):
        """뉴스 본문 텍스트 추출"""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=2) # 타임아웃 짧게
            if response.status_code != 200: return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 네이버 뉴스
            if "news.naver.com" in url:
                content = soup.select_one("#dic_area")
                return self.clean_html(content.get_text(strip=True)) if content else ""
            
            # 일반 뉴스
            paragraphs = soup.find_all('p')
            full_text = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30])
            return full_text[:1500]
            
        except Exception:
            return ""

    def search_news(self, keyword, market="KR", display=5):
        """네이버 검색 + 상위 3개 Deep Crawling"""
        try:
            print(f"🔍 [{keyword}] 뉴스 검색 시작...")
            query = f"{keyword} 특징주" if market == "KR" else keyword
            params = {"query": query, "display": display, "sort": "date"}
            
            res = requests.get(self.naver_base_url, headers=self.naver_headers, params=params, timeout=3)
            
            if res.status_code == 200:
                items = res.json().get('items', [])
                processed_news = []
                
                for idx, item in enumerate(items):
                    title = self.clean_html(item['title'])
                    link = item['originallink'] or item['link']
                    desc = self.clean_html(item['description'])
                    content_to_use = desc

                    # 상위 3개만 Deep Crawling
                    if idx < 3:
                        body = self.fetch_article_body(link)
                        if len(body) > 50: content_to_use = body
                    
                    processed_news.append(f"- 제목: {title}\n- 내용: {content_to_use}\n- 링크: {link}")
                
                print(f"✅ 총 {len(processed_news)}개의 뉴스 확보")
                return processed_news
            return []
        except Exception as e:
            print(f"❌ [검색 에러] {e}")
            return []

    # --------------------------------------------------------------------------
    # 🧠 AI 요약 엔진 (라우터)
    # --------------------------------------------------------------------------
    async def summarize_news(self, stock_name, news_data):
        if not news_data: return None

        if AI_PROVIDER == "GEMINI":
            return await self._use_gemini(stock_name, news_data)
        elif AI_PROVIDER == "LOCAL":
            return await self._use_local_llm(stock_name, news_data)
        elif AI_PROVIDER == "MOCK":
            return await self._use_mock(stock_name, news_data)
        else:
            return None

    # 1. Gemini
    async def _use_gemini(self, stock_name, news_data):
        if not self.gemini_model: return None
        news_text = "\n\n".join(news_data)
        prompt = self._get_prompt(stock_name, news_text)
        
        try:
            loop = asyncio.get_running_loop()
            # Gemini 호출은 동기 함수이므로 executor 사용
            response = await loop.run_in_executor(None, self.gemini_model.generate_content, prompt)
            return self._parse_json_response(response.text)
        except Exception as e:
            print(f"❌ [Gemini 에러] {e}")
            return None

    # 2. Local LLM
    async def _use_local_llm(self, stock_name, news_data):
        news_text = "\n\n".join(news_data)
        system_prompt = self._get_prompt(stock_name, "", only_system=True) # 프롬프트 재사용

        payload = {
            "model": LOCAL_MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"다음 뉴스들을 분석하고 JSON으로 답해:\n{news_text}"}
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
            "stream": False
        }

        try:
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None, 
                lambda: requests.post(LOCAL_LLM_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=120)
            )
            
            if res.status_code == 200:
                content = res.json()['choices'][0]['message']['content']
                print(f"\n🤖 [AI 응답] {content[:50]}...")
                return self._parse_json_response(content)
            else:
                print(f"⚠️ [Local LLM 실패] {res.status_code}")
                return None
        except Exception as e:
            print(f"❌ [Local LLM 에러] {e}")
            return None

    # 3. Mock
    async def _use_mock(self, stock_name, news_data):
        await asyncio.sleep(0.5)
        return {
            "summary": f"1. [테스트] {stock_name} 관련 뉴스 감지됨\n2. Mock 모드라 비용 0원\n3. Gemini/Local로 전환하세요.",
            "sentiment": "Neutral",
            "key_trigger": "개발 테스트 진행 중"
        }

    # --- 헬퍼 함수 ---
    def _get_prompt(self, stock_name, news_text, only_system=False):
        system = f"""
        당신은 주식 시장 분석가입니다. '{stock_name}' 관련 뉴스를 분석하여 다음을 JSON으로 반환하세요:
        1. key_trigger: 주가 변동의 핵심 원인 (팩트/숫자 위주)
        2. market_reaction: 시장 반응 (수급, 목표가 등)
        3. summary: 3줄 요약
        4. sentiment: Positive/Negative/Neutral
        """
        if only_system: return system
        return f"{system}\n\n[뉴스 데이터]\n{news_text}"

    def _parse_json_response(self, raw_text):
        try:
            text = raw_text.strip()
            if "</think>" in text: text = text.split("</think>")[-1].strip()
            if "```" in text:
                parts = text.split("```")
                for part in parts:
                    if "{" in part: 
                        text = part.replace("json", "").strip()
                        break
            
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                return ujson.loads(text[start:end+1])
            return None
        except:
            return None


    # ==========================================================================
    # 🏃 메인 실행 로직 (Worker Mode)
    # ==========================================================================
    async def run(self):
        print(f"📰 [뉴스팀] News Crawler 가동! (Mode: {AI_PROVIDER})")
        
        redis_host = getattr(settings, 'REDIS_HOST', 'localhost') 
        r = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
        pubsub = r.pubsub()
        
        channel = getattr(settings, 'REDIS_CHANNEL_STOCK', 'stock_alert')
        await pubsub.subscribe(channel)

        try:
            print(f"👂 Redis 채널 '{channel}' 구독 중...")
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data_str = message['data']
                    print(f"⚡ [신호 수신] {data_str}")
                    
                    try:
                        data = ujson.loads(data_str)
                        keyword = data.get('name') or data.get('keyword')
                        code = data.get('code')
                        market = data.get('market', 'KR')
                    except:
                        keyword = data_str
                        code = None
                        market = 'KR'

                    if not keyword: continue

                    print(f"🕵️ [분석 시작] '{keyword}'")
                    
                    loop = asyncio.get_running_loop()
                    news_list = await loop.run_in_executor(None, self.search_news, keyword, market)
                    
                    if news_list:
                        ai_result = await self.summarize_news(keyword, news_list[:5])
                        
                        # [수정 1] 데이터 포맷팅 안전장치 (리스트 -> 문자열 변환)
                        summary = "분석 실패"
                        sentiment = "Neutral"
                        key_trigger = ""
                        market_reaction = ""
                        link = news_list[0].split("링크: ")[-1] if news_list else ""

                        if ai_result:
                            # 요약이 리스트(['1. ...', '2. ...'])로 오면 줄바꿈으로 합치기
                            raw_summary = ai_result.get('summary')
                            if isinstance(raw_summary, list):
                                summary = "\n".join(raw_summary)
                            else:
                                summary = str(raw_summary)
                            
                            sentiment = ai_result.get('sentiment', sentiment)
                            key_trigger = ai_result.get('key_trigger', "")
                            market_reaction = ai_result.get('market_reaction', "")

                        # [수정 2] Main 서버 포맷에 맞게 평평하게(Flat) 전송
                        payload = {
                            "type": "NEWS_SUMMARY",
                            "code": code,
                            "name": keyword,
                            "summary": summary,            # 최상위 키
                            "sentiment": sentiment,        # 최상위 키
                            "key_trigger": key_trigger,    # (옵션) 추가 정보
                            "market_reaction": market_reaction, # (옵션) 추가 정보
                            "link": link
                        }
                        
                        await r.publish("news_alert", ujson.dumps(payload))
                        print(f"✅ [전송 완료] news_alert 발행: {summary[:30]}...")
                    else:
                        print("💨 뉴스 없음")

        except Exception as e:
            print(f"❌ [Worker Error] {e}")
        finally:
            await r.aclose()

# ==========================================================================
# 🧪 테스트 실행 블록
# ==========================================================================
if __name__ == "__main__":
    async def test():
        print("\n🔎 [1단계] 설정 확인 중...")
        crawler = NewsCrawler()
        
        test_redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

        keyword = "삼성전자"
        print(f"\n🔎 [2단계] 뉴스 검색 테스트 ({keyword})")
        news = crawler.search_news(keyword, "KR")
        print(f"   👉 뉴스 개수: {len(news)}")
        
        if news:
            print(f"\n🔎 [3단계] AI 요약 테스트 (Mode: {AI_PROVIDER})")
            res = await crawler.summarize_news(keyword, news)
            
            if res:
                print(f"\n✅ [성공] AI 원본 결과:\n{res}")
                
                # [핵심 수정] "data" 안에 넣지 않고, 바로 풉니다!
                
                # 리스트 처리
                final_summary = res.get('summary', '요약 없음')
                if isinstance(final_summary, list):
                    final_summary = "\n".join(final_summary)

                payload = {
                    "type": "NEWS_SUMMARY",
                    "name": keyword,
                    "summary": final_summary,        # 👈 Main이 찾는 키!
                    "sentiment": res.get('sentiment', 'Neutral'), # 👈 Main이 찾는 키!
                    "key_trigger": res.get('key_trigger', ''),
                    "market_reaction": res.get('market_reaction', ''),
                    "link": news[0].split("링크: ")[-1]
                }
                
                # 실제 전송
                await test_redis.publish("news_alert", ujson.dumps(payload))
                print(f"\n📡 [테스트] Redis Publish 완료!")
                print(f"   보낸 데이터: {ujson.dumps(payload, ensure_ascii=False)[:100]}...")
            else:
                print("❌ AI 분석 실패")
        
        await test_redis.aclose()

    asyncio.run(test())