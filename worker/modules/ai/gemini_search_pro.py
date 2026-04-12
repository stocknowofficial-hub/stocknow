import asyncio
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from common.config import settings
import pytz
from worker.modules.ai.prompts import get_briefing_prompt

class GeminiSearchPro:
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            print("⚠️ [Gemini Pro] API 키가 없습니다.")
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
                print(f"✨ [Gemini Pro] 브리핑 전용 엔진 가동 (Model: gemini-2.5-flash)")
            except Exception as e:
                print(f"❌ [Gemini Pro] 초기화 실패: {e}")
                self.client = None

    def _generate_sync(self, prompt):
        return self.client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2, # 정보를 다루므로 창의성(1.0)보다 정확성(0.2) 중시
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )

    async def search_and_summarize(self, query, link_keyword=None, mode='KR_MID', original_url=None, post_time=None):
        """
        Broadcasting Logic (KR/US x Opening/Mid/Close)
        """
        if not self.client: return None

        print(f"🧐 [Gemini Pro] 심층 브리핑 생성 중... '{query}' (Mode: {mode})")

        # 🕒 [Timezone Calculation]
        utc_now = datetime.now(pytz.utc)
        ny_tz = pytz.timezone('America/New_York')
        kr_tz = pytz.timezone('Asia/Seoul')
        
        ny_time = utc_now.astimezone(ny_tz)
        kr_time = utc_now.astimezone(kr_tz)
        
        ny_str = ny_time.strftime("%H:%M")
        kr_str = kr_time.strftime("%H:%M")
        today_full = kr_time.strftime("%Y년 %m월 %d일 %A") # 한국 기준 날짜

        # ✅ [시간 포맷팅] post_time이 넘어오면 (트럼프 등) 예쁘게 변환
        post_time_str = None
        if post_time:
            try:
                # ISO 문자열 (2026-01-11T03:25:00Z 등) 파싱 시도
                # Z가 있으면 replace로 날리고 처리 (간단 버전)
                dt_str = post_time.replace('Z', '+00:00')
                dt_obj = datetime.fromisoformat(dt_str)
                # 한국 시간으로 변환
                dt_kr = dt_obj.astimezone(kr_tz)
                post_time_str = dt_kr.strftime("%Y년 %m월 %d일 %A %H:%M (KST)")
            except:
                # 파싱 실패하면 그냥 원본 사용
                post_time_str = str(post_time)

        # 🤖 [AI 지시사항] - 외부 파일(prompts.py)에서 가져옴
        header_title, prompt = get_briefing_prompt(mode, query, today_full, ny_str, kr_str, post_time_str=post_time_str)

        # 🚀 실행 및 파싱 (Run & Parse)
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, self._generate_sync, prompt)

            if response and response.text:
                text = response.text.strip()
                
                # 🚨 [Noise Filter]
                if "SKIP" in text and len(text) < 10:
                    return {
                        "summary": "SKIP",
                        "sentiment": "Neutral",
                        "link": ""
                    }

                # 🧠 AI 감성 판단 파싱 (Sentiment Parsing)
                sentiment = "Neutral"
                if "[Sentiment: Positive]" in text:
                    sentiment = "Positive"
                    text = text.replace("[Sentiment: Positive]", "").strip()
                elif "[Sentiment: Negative]" in text:
                    sentiment = "Negative"
                    text = text.replace("[Sentiment: Negative]", "").strip()
                elif "[Sentiment: Neutral]" in text:
                    sentiment = "Neutral"
                    text = text.replace("[Sentiment: Neutral]", "").strip()

                # 🏷️ [Metadata Parsing] (Sectors & Topics)
                sectors = None
                topics = None
                
                if "[Sectors:" in text:
                    try:
                        part = text.split("[Sectors:")[1].split("]")[0]
                        sectors = part.strip()
                        text = text.replace(f"[Sectors:{part}]", "").strip()
                    except: pass
                    
                if "[Topics:" in text:
                    try:
                        part = text.split("[Topics:")[1].split("]")[0]
                        topics = part.strip()
                        text = text.replace(f"[Topics:{part}]", "").strip()
                    except: pass

                # ✅ [헤더 병합]
                if header_title:
                    text = f"{header_title}\n\n{text}"
                
                # 🧹 [후처리]
                text = text.replace("**", "")
                
                # 링크 생성
                if original_url:
                    final_link = original_url
                else:
                    target_q = link_keyword if link_keyword else query
                    encoded_query = target_q.replace(" ", "+")
                    final_link = f"https://www.google.com/search?q={encoded_query}&tbm=nws"

                return {
                    "summary": text,
                    "link": final_link,
                    "sentiment": sentiment,
                    "sectors": sectors, # ✅ New
                    "topics": topics    # ✅ New
                }
            return None

        except Exception as e:
            print(f"⚠️ [Gemini Pro] 호출 실패: {e}")
            return None

    async def analyze_report_file(self, source, title, file_path):
        """
        주간 리포트(PDF) 파일 기반 심층 분석 (Multimodal)
        """
        if not self.client: return None
        
        from worker.modules.ai.prompts import get_report_analysis_prompt
        # 프롬프트는 텍스트 입력 없이 지침만 가져옴 (is_file_mode=True)
        prompt = get_report_analysis_prompt(source, text="", is_file_mode=True)
        
        print(f"🧠 [Gemini Pro] 리포트 파일 분석 중... [{source}] {title}")
        
        try:
            # 1. Upload File with 'genai-Client' compatible way
            # Note: google.genai V2 Client uses client.files.upload
            loop = asyncio.get_running_loop()
            
            # Helper for synchronous file upload
            def upload_and_generate():
                with open(file_path, "rb") as f:
                    uploaded_file = self.client.files.upload(file=f, config={'mime_type': 'application/pdf'})
                
                # Wait for processing? Usually PDF is fast, but larger video needs wait. 
                # For PDF, immediate generation usually works or we wait for STATE==ACTIVE.
                # Assuming simple upload works for now.
                
                response = self.client.models.generate_content(
                    model='gemini-3-flash-preview',
                    contents=[prompt, uploaded_file],
                    config=types.GenerateContentConfig(temperature=0.2)
                )
                return response
            
            # Run in executor (2.5-flash thinking model은 응답이 느릴 수 있어 240초 타임아웃)
            response = await asyncio.wait_for(
                loop.run_in_executor(None, upload_and_generate),
                timeout=240.0
            )
            
            if response and response.text:
                result_text = response.text.strip()
                
                # 🏷️ [Metadata Parsing] (Same Logic)
                sentiment = "Neutral"
                sectors = None
                topics = None
                
                if "[Sentiment: Positive]" in result_text: sentiment = "Positive"
                elif "[Sentiment: Negative]" in result_text: sentiment = "Negative"
                elif "[Sentiment: Neutral]" in result_text: sentiment = "Neutral"
                result_text = result_text.replace(f"[Sentiment: {sentiment}]", "").strip()

                if "[Sectors:" in result_text:
                    try:
                        part = result_text.split("[Sectors:")[1].split("]")[0]
                        sectors = part.strip()
                        result_text = result_text.replace(f"[Sectors:{part}]", "").strip()
                    except: pass
                
                if "[Topics:" in result_text:
                    try:
                        part = result_text.split("[Topics:")[1].split("]")[0]
                        topics = part.strip()
                        result_text = result_text.replace(f"[Topics:{part}]", "").strip()
                    except: pass
                
                # Clean up leftovers
                result_text = result_text.replace("[METADATA]", "").strip()
                result_text = result_text.replace("------------------------------", "").strip()
                # Remove hallucinated link placeholders if any
                if "🔗 [관련 뉴스]()" in result_text:
                    result_text = result_text.replace("🔗 [관련 뉴스]()", "")
                
                result_text = result_text.replace("**", "")
                
                return {
                    "summary": result_text,
                    "sentiment": sentiment,
                    "sectors": sectors,
                    "topics": topics
                }
        except asyncio.TimeoutError:
            print(f"⏰ [Gemini Pro] 리포트 파일 분석 타임아웃 (240s): [{source}] {title}")
            return None
        except Exception as e:
            print(f"❌ [Gemini Pro] 리포트 파일 분석 실패: {e}")
            return None
