import asyncio
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from common.config import settings

class GeminiSearchPro:
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            print("⚠️ [Gemini Pro] API 키가 없습니다.")
            self.client = None
        else:
            try:
                # 🚀 User Requested Model: gemini-3-pro-preview
                self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
                print(f"✨ [Gemini Pro] 브리핑 전용 엔진 가동 (Model: gemini-3-pro-preview)")
            except Exception as e:
                print(f"❌ [Gemini Pro] 초기화 실패: {e}")
                self.client = None

    def _generate_sync(self, prompt):
        return self.client.models.generate_content(
            model='gemini-3-pro-preview', 
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2, # 정보를 다루므로 창의성(1.0)보다 정확성(0.2) 중시
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )

    async def search_and_summarize(self, query, link_keyword=None, mode='KR_MID'):
        """
        Broadcasting Logic (KR/US x Opening/Mid/Close)
        """
        if not self.client: return None

        print(f"🧐 [Gemini Pro] 심층 브리핑 생성 중... '{query}' (Mode: {mode})")

        # 🕒 [Timezone Calculation]
        import pytz
        utc_now = datetime.now(pytz.utc)
        ny_tz = pytz.timezone('America/New_York')
        kr_tz = pytz.timezone('Asia/Seoul')
        
        ny_time = utc_now.astimezone(ny_tz)
        kr_time = utc_now.astimezone(kr_tz)
        
        ny_str = ny_time.strftime("%H:%M")
        kr_str = kr_time.strftime("%H:%M")
        today_full = kr_time.strftime("%Y년 %m월 %d일 %A") # 한국 기준 날짜

        # 헤더 타이틀을 Python에서 직접 주입 (AI 날짜 혼동 방지)
        header_title = None

        # 기본 공통 Rule
        base_rule = f"""
        [Target News Date] Focus on the verifiable LATEST real-time news.
        [Language] Korean (한국어)
        [Tone] Professional, Concise, Insightful (Investment Analyst Style)
        [Formatting Rules]
        - **NO HEADERS**: Do NOT include a main title (e.g. "Briefing"). Start directly with the first section.
        - Do NOT use Markdown headers (#, ##).
        - Use distinct emojis for headers.
        - **STRICTLY FORBIDDEN**: Do NOT use bold text (**). Write EVERYTHING in plain text.
        - **Keep it Concise**: Max 3-4 bullet points per section. Avoid long paragraphs.
        """

        # ==============================================================================
        # 🇰🇷 한국장 프롬프트 (KR)
        # ==============================================================================
        if mode == 'KR_OPENING':
            header_title = f"🇰🇷 한국 증시 장 시작전 브리핑 ({today_full})"
            prompt = f"""
            {base_rule}
            [Task] Search for "{query}" and write a 'Market Opening Briefing' for Korea.
            
            [Structure]
            1. 📅 [오늘의 일정]
               - Key economic events, earnings releases, or policy announcements today.
            2. 📈 [시장 전망]
               - Expected market flow based on overnight US market and global sentiment.
            3. ⚠️ [리스크 및 변수]
               - Negative factors, exchange rate risks, or geopolitical issues.
            4. 🧐 [관전 포인트]
               - Sectors or themes to watch closely today.
            """
            
        elif mode == 'KR_MID':
            header_title = f"🇰🇷 한국 증시 장중 브리핑 ({today_full})"
            prompt = f"""
            {base_rule}
            [Task] Search for "{query}" and write a 'Mid-Day Market Briefing' for Korea.
            
            [Structure]
            1. 📈 [오전 상승 주도]
               - Top performing sectors/themes and WHY they are rising.
            2. 📉 [오전 약세 흐름]
               - Weak sectors and reasons for the decline.
            3. 🚀 [특징주 코멘트]
               - Individual stocks with significant news/movement (Top 2-3).
            4. 📝 [장중 시황 요약]
               - Summary of KOSPI/KOSDAQ flow and Foreigner/Institution supply status.
            """

        elif mode == 'KR_CLOSE':
            header_title = f"🇰🇷 한국 증시 마감 브리핑 ({today_full})"
            prompt = f"""
            {base_rule}
            [Task] Search for "{query}" and write a 'Market Closing Briefing' for Korea.
            
            [Structure]
            1. 🏁 [마감 총평]
               - Summary of KOSPI/KOSDAQ closing levels and main drivers.
            2. 🏆 [오늘의 승자/패자]
               - Best/Worst performing sectors analysis.
            3. 💡 [내일의 투자 아이디어]
               - Based on today's flow, what should we prepare for tomorrow?
            """

        # ==============================================================================
        # 🇺🇸 미국장 프롬프트 (US)
        # ==============================================================================
        elif mode == 'US_OPENING':
            # ✅ [수정] Python에서 헤더 직접 생성 (시간 강제 주입)
            header_title = f"🇺🇸 미국 증시 장 시작전 브리핑 ({today_full})\n\n[기준: 미 동부시간 {ny_str} / 한국시간 {kr_str}]"
            
            prompt = f"""
            {base_rule}
            [Task] Search for "{query}" and write a 'Market Opening Briefing' for US Market.
            
            [Structure]
            1. 🌅 [오늘의 이슈 & 전망]
               - Key macro events (Fed, CPI, etc.) and market outlook for today.
            2. 📊 [유망/하락 예상 섹터]
               - Which sectors are expected to be strong/weak based on pre-market data?
            3. ⚠️ [투자자 유의사항]
               - Volatility risks, Bond yields, or specific stock warnings.
            4. 💡 [장초반 대응 전략] (Action Plan)
               - Practical advice: "Buy on dip", "Watch and wait", or "Focus on Tech".
            """

        elif mode == 'US_MID':
            header_title = f"🇺🇸 미국 증시 장중 브리핑 ({today_full})\n\n[기준: 미 동부시간 {ny_str} / 한국시간 {kr_str}]"
            prompt = f"""
            {base_rule}
            [Task] Search for "{query}" and write a 'Mid-Day Briefing' for US Market.
            
            [Structure]
            1. 📝 [오전장 요약]
               - Summary of market flow from Opening to now (Gap-up/down, Reversal, etc.).
            2. 🚀 [특징주 & 수급]
               - Stocks with massive volume or price change today.
            3. 💡 [남은 시간 대응법] (Action Plan)
               - How to handle the rest of the trading session? (Profit taking / Bargain hunting).
            """

        elif mode == 'US_CLOSE':
            header_title = f"🇺🇸 미국 증시 마감 브리핑 ({today_full})\n\n[기준: 미 동부시간 {ny_str} / 한국시간 {kr_str}]"
            prompt = f"""
            {base_rule}
            [Task] Search for "{query}" and write a 'Market Closing Briefing' for US Market.
            
            [Structure]
            1. 🏁 [마감 이슈 & 원인]
               - Why did the market rise/fall today? (Main drivers).
            2. 🚀 [오늘의 급등/급락]
               - Top gainers and losers in major sectors.
            3. 🎓 [오늘의 교훈] (Lessons)
               - What should investors learn from today's market?
            4. 🌙 [내일 준비 & 애프터마켓]
               - Key events to watch for tomorrow or After-hours movers.
            """

        else:
            prompt = base_rule + f"\n[Task] Summarize the latest news for: {query}"

        # 🚀 실행
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, self._generate_sync, prompt)

            if response and response.text:
                text = response.text.strip()
                
                # ✅ [헤더 병합] Python에서 생성한 정밀 타이틀을 붙여넣기
                if header_title:
                    # AI가 혹시나 또 제목을 만들었을 수 있으므로, 첫 줄이 '미국 증시' 등으로 시작하면 제거 시도 (선택적)
                    # 여기서는 가장 확실한 방법인 "Bold 제거" 및 "헤더 결합"만 수행
                    text = f"{header_title}\n\n{text}"
                
                # 🧹 [후처리] AI가 말을 안 듣고 Bold를 썼을 경우 강제 제거
                text = text.replace("**", "")
                
                # 링크 생성
                target_q = link_keyword if link_keyword else query
                encoded_query = target_q.replace(" ", "+")
                final_link = f"https://www.google.com/search?q={encoded_query}&tbm=nws"

                return {
                    "summary": text,
                    "link": final_link,
                    "sentiment": "Neutral"
                }
            return None

        except Exception as e:
            print(f"⚠️ [Gemini Pro] 호출 실패: {e}")
            return None
