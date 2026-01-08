import asyncio
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from common.config import settings

class GeminiSearch:
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            print("⚠️ [Gemini] API 키가 없습니다.")
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
                print(f"✨ [Gemini] 메인 엔진 준비 완료 (Model: gemini-2.0-flash)")
            except Exception as e:
                print(f"❌ [Gemini] 초기화 실패: {e}")
                self.client = None

    def _generate_sync(self, prompt):
        return self.client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )

    async def search_and_summarize(self, query, link_keyword=None, mode='default'):
        """
        query: Gemini에게 던질 복잡한 질문
        link_keyword: 사용자에게 보여줄 깔끔한 검색어 (없으면 query 사용)
        """
        if not self.client: return None

        print(f"🚀 [Gemini] 검색 요청: '{query}' (Mode: {mode})")

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        # 🤖 [AI 지시사항]
        # 1. 한국어로 3줄 요약해라.
        # 2. 뉴스 내용을 분석해서 주가에 긍정(Positive)/부정(Negative)/중립(Neutral)인지 판단해라.
        # 3. 마지막 줄에 [Sentiment: Positive] 형식으로 태그를 달아라.
        if mode == 'default':
            prompt = f"""
            [Task] Perform a Google Search for: "{query}"
            
            [Strict Filtering Rules]
            1. **Time Limit:** IGNORE any news older than **48 hours**. STRICTLY focus on Real-time/Today's news.
            2. **RelevanceCheck:** 
               - If Stock is DOWN -> Look for NEGATIVE reasons.
               - If Stock is UP -> Look for POSITIVE reasons.
               - If news contradicts the trend (e.g. -5% but "Analyst Buy"), treat as irrelevant/old -> Ignore.

            [Output Rules]
            1. **Language:** ANSWER IN **KOREAN** (한국어).
            2. **Format:** Summarize 3 key bullet points (*). Do NOT use bold text (**).
            3. **Decision:**
               - **Found valid news:** Output the 3 bullet points.
               - **No valid/recent news:** Output EXACTLY: "NO_NEWS_FOUND"

            [Example Output - Success]
            * 엔비디아, 새로운 AI 칩셋 'Blackwell' 출시 발표
            * 월가 목표 주가 상향 조정 (150$ -> 180$)
            * 실적 발표를 앞두고 구글, MS 등 주요 고객사 수요 증가 확인

            [Example Output - Failure]
            NO_NEWS_FOUND
            """

        elif mode == 'opening_briefing':
            prompt = f"""
            [Current Date] {today_str}
            [Task] Perform a Google Search for: "{query}" and provide a morning briefing for Korean stock market.

            [Strict Output Rules]
            1. **Language:** ANSWER IN **KOREAN** (한국어).
            2. **Structure:** You MUST use the following 4 sections exactly:
               - 📅 [주요 일정] (Key Schedule today/this week)
               - 📈 [오늘의 기대] (Market Outlook/Positive factors)
               - ⚠️ [주의할 점] (Risks/Negative factors)
               - 🧐 [오늘의 관전 포인트] (Key themes/Simultaneous stock sectors to watch)
            3. **Content:** Be concise and professional (suitable for Telegram messenger).
            4. **Constraint:** Focus on news from **{yesterday_str}** to **{today_str}**.
            5. **Sentiment Analysis:** Analyze overall market sentiment.
            6. **Final Tag:** The LAST LINE must be exactly one of:
               - [Sentiment: Positive]
               - [Sentiment: Negative]
               - [Sentiment: Neutral]

            [Example Output]
            📅 [주요 일정]
            * 금융통화위원회 기준금리 결정 (10:00)
            * 삼성전자 잠정 실적 발표 예정

            📈 [오늘의 기대]
            * 간밤 나스닥 반도체주 강세로 인한 국내 반도체 섹터 수급 유입 기대
            * 외국인 선물 매수세 지속 가능성

            ⚠️ [주의할 점]
            * 중동 지정학적 리스크 재부각에 따른 유가 변동성 확대
            * 원/달러 환율 1,350원 상향 돌파 시도

            🧐 [오늘의 관전 포인트]
            * 반도체 소부장(HBM 관련주), 방산, 해운
            [Sentiment: Neutral]
            """
        elif mode == 'mid_briefing':
            prompt = f"""
            [Current Date] {today_str}
            [Task] Perform a Google Search for: "{query}" and provide a mid-day briefing for Korean stock market.

            [Strict Output Rules]
            1. **Language:** ANSWER IN **KOREAN** (한국어).
            2. **Structure:** You MUST use the following 4 sections exactly:
               - 📈 [오전 상승 섹터] (Top performing sectors/themes)
               - 📉 [오전 하락 섹터] (Weak sectors)
               - 🚀 [오늘의 특징주] (Notable stocks moving on news)
               - 📝 [오전 시황 요약] (Summary of market flow)
            3. **Content:** Be concise and professional. Focus on WHY they are moving.
            4. **Constraint:** Focus on news from **{yesterday_str}** to **{today_str}**.
            5. **Sentiment Analysis:** Analyze overall market sentiment.
            6. **Final Tag:** The LAST LINE must be exactly one of:
               - [Sentiment: Positive]
               - [Sentiment: Negative]
               - [Sentiment: Neutral]

            [Example Output]
            📈 [오전 상승 섹터]
            * 반도체: 엔비디아 효과로 SK하이닉스, 한미반도체 강세
            * 2차전지: 테슬라 인도량 호조에 에코프로비엠 급등

            📉 [오전 하락 섹터]
            * 제약바이오: 차익 실현 매물 출회로 전반적 약세
            * 건설: PF 우려 지속으로 대형 건설사 신저가

            🚀 [오늘의 특징주]
            * 삼성전자: 외국인 대량 매수로 7만전자 회복 시도
            * 카카오: 경영진 사법 리스크 재부각에 급락

            📝 [오전 시황 요약]
            * 코스피는 외인/기관 양매수로 상승 출발했으나 환율 부담에 상승폭 축소
            * 코스닥은 2차전지 주도로 1%대 강세 유지
            [Sentiment: Positive]
            """
        else:
            prompt = f"""
            [Current Date] {today_str}
            [Task] Perform a Google Search for: "{query}"
            
            [Strict Output Rules]
            1. **Language:** ANSWER IN **KOREAN** (한국어).
            2. **Format:** Use bullet points (*). Exactly 3 key points.
            3. **Final Tag:** The LAST LINE must be exactly one of: 
               - [Sentiment: Positive]
               - [Sentiment: Negative]
               - [Sentiment: Neutral]
            """

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, self._generate_sync, prompt)

            if response and response.text:
                text = response.text.strip()
                
                # 🚨 [엄격 모드] 뉴스 없음 처리
                if "NO_NEWS_FOUND" in text or "NO_NEWS" in text:
                    # 뉴스는 없지만, '정보 없음'이라는 상태를 리턴해야 함 (봇이 알림은 보내야 하니까)
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

                return {
                    "summary": summary_text,
                    "link": final_link,
                    "sentiment": sentiment
                }
            return None

        except Exception as e:
            print(f"⚠️ [Gemini] 호출 실패: {e}")
            return None