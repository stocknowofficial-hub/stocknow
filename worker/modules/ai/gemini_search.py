import asyncio
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from common.config import settings
from worker.modules.ai.prompts import get_stock_analysis_prompt

class GeminiSearch:
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            print("⚠️ [Gemini] API 키가 없습니다.")
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
                print(f"✨ [Gemini] 메인 엔진 준비 완료 (Model: gemini-2.5-flash)")
            except Exception as e:
                print(f"❌ [Gemini] 초기화 실패: {e}")
                self.client = None

    def _generate_sync(self, prompt):
        return self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )

    async def search_and_summarize(self, query, link_keyword=None, mode='default', market_context=None, rate=None):
        """
        query: Gemini에게 던질 복잡한 질문
        link_keyword: 사용자에게 보여줄 깔끔한 검색어 (없으면 query 사용)
        market_context: 과거 분석 기록 문자열 (Context Injection)
        rate: 실제 등락률 (할루시네이션 방지용 주입)
        """
        if not self.client: return None

        print(f"🚀 [Gemini] 검색 요청: '{query}' (Mode: {mode})")

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        # 🤖 [AI 지시사항] - 외부 파일(prompts.py)에서 가져옴
        prompt = get_stock_analysis_prompt(query, today_str, yesterday_str, market_context=market_context, rate=rate)

        try:
            loop = asyncio.get_running_loop()
            # ⏱️ [Safety] 45초 타임아웃 설정 (무한 대기 방지)
            response = await asyncio.wait_for(
                loop.run_in_executor(None, self._generate_sync, prompt),
                timeout=45.0
            )

            if response and response.text:
                text = response.text.strip()
                
                # 🚨 [엄격 모드] 뉴스 없음 처리
                if "NO_NEWS_FOUND" in text or "NO_NEWS" in text:
                    target_q = link_keyword if link_keyword else query
                    encoded_query = target_q.replace(" ", "+")
                    return {
                        "summary": None, # 요약 없음
                        "sentiment": "Unknown", # 판단 불가
                        "link": f"https://www.google.com/search?q={encoded_query}&tbm=nws"
                    }

                # ---------------------------------------------------------
                # 🧠 AI 감성 판단 파싱 (Sentiment Parsing)
                # ---------------------------------------------------------
                sentiment = "Neutral" # 기본값
                
                if "[Sentiment: Positive]" in text:
                    sentiment = "Positive"
                    text = text.replace("[Sentiment: Positive]", "").strip()
                elif "[Sentiment: Negative]" in text:
                    sentiment = "Negative"
                    text = text.replace("[Sentiment: Negative]", "").strip()
                elif "[Sentiment: Neutral]" in text:
                    sentiment = "Neutral"
                    text = text.replace("[Sentiment: Neutral]", "").strip()

                # ---------------------------------------------------------
                # 🔗 링크 생성 (깔끔한 검색어 적용)
                # ---------------------------------------------------------
                target_q = link_keyword if link_keyword else query
                encoded_query = target_q.replace(" ", "+")
                final_link = f"https://www.google.com/search?q={encoded_query}&tbm=nws"

                # 요약 본문 정리 (혹시 모를 공백 제거)
                start_index = text.find('*')
                summary_text = text[start_index:] if start_index != -1 else text

                # 🧹 [Cleanup] AI Tutor Note가 없거나 None인 경우 제거
                if "(AI Tutor Note: None)" in summary_text or "(AI Tutor Note: N/A)" in summary_text:
                    summary_text = summary_text.replace("(AI Tutor Note: None)", "")
                    summary_text = summary_text.replace("(AI Tutor Note: N/A)", "")
                    summary_text = summary_text.strip()

                return {
                    "summary": summary_text,
                    "link": final_link,
                    "sentiment": sentiment
                }
            return None

        except Exception as e:
            print(f"⚠️ [Gemini] 호출 실패: {e}")
            return None