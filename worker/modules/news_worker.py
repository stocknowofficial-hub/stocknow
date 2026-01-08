import asyncio
import ujson
import redis.asyncio as redis
import pytz # ✅ 시차 해결을 위해 추가
from datetime import datetime
from common.config import settings
from worker.modules.ai.gemini_search import GeminiSearch
from worker.modules.ai.gemini_search_pro import GeminiSearchPro

class NewsWorker:
    def __init__(self):
        print(f"📰 [NewsWorker] Dual Engine Mode (Flash=Stocks, Pro=Briefing)")
        self.gemini = GeminiSearch()           # 속도 (종목 분석용)
        self.gemini_pro = GeminiSearchPro()    # 지능 (시황 브리핑용)

    async def process_pipeline(self, msg_data):
        """
        시장(Market)에 따라 최적의 검색 언어와 날짜, 프롬프트를 선택합니다.
        """
        msg_type = msg_data.get('type')
        market = msg_data.get('market', 'KR')
        
        # -----------------------------------------------------
        # 🕒 [Timezone 처리] 한국 vs 미국 날짜 분리
        # -----------------------------------------------------
        # 1. 한국 시간 (시스템 시간)
        now_kr = datetime.now()
        date_str_kr = now_kr.strftime("%Y년 %m월 %d일") # 예: 2026년 1월 5일

        # 2. 미국 뉴욕 시간 (API 검색용)
        # 🚨 한국이 1/5 새벽이어도, 미국은 1/4 낮일 수 있음 -> 검색 정확도 핵심!
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        # date_str_us = now_ny.strftime("%Y-%m-%d") (삭제: 날짜 혼동 방지)
        
        # -----------------------------------------------------
        # A. 급등주 분석 (CONDITION)
        # -----------------------------------------------------
        if msg_type in ['CONDITION', 'CONDITION_US']:
            code = msg_data.get('code') 
            name = msg_data.get('name') 
            rate = msg_data.get('rate', '0')
            is_bullish = float(rate) > 0
            
            query = ""
            clean_keyword = "" 

            # 🇰🇷 [한국장 전략] -> 한국 시간 사용
            if market == 'KR':
                move_type = "급등" if is_bullish else "급락"
                query = f"{date_str_kr} {name} 주가 {move_type} 이유와 관련 최신 뉴스 3줄 요약"
                clean_keyword = name 

            # 🇺🇸 [미국장 전략] -> 뉴욕 시간 사용
            else:
                # ✅ [Link Fix] "인텔 (INTC)" 처럼 한글 섞이면 구글 뉴스 링크 깨짐 -> "Code stock"으로 통일
                clean_keyword = f"{code} stock"
                
                # ✅ [AI Query] "Target: ..." 같은 지시사항을 넣으면 검색어 오염됨.
                # 그냥 자연스럽게 풀네임을 문장에 녹이는 게 검색율 가장 좋음 (Step 838 회귀 + 링크 유지)
                search_subject = f"{name} ({code})"
                
                if is_bullish:
                    query = f"Why is {search_subject} stock up today? latest news and analyst rating. (Answer in Korean)"
                else:
                    query = f"Why is {search_subject} stock down today? latest news and major issues. (Answer in Korean)"
            
            print(f"🧠 [Gemini 요청] {query} / [Link] {clean_keyword}")
            return await self.gemini.search_and_summarize(query, link_keyword=clean_keyword)

        # -----------------------------------------------------
        # B. 시황 브리핑 (MARKET_BRIEFING)
        # -----------------------------------------------------
        elif msg_type == 'MARKET_BRIEFING':
            subtype = msg_data.get('subtype') # OPENING, MID, CLOSE
            
            # 모드 조합 (예: KR_OPENING)
            pro_mode = f"{market}_{subtype}"
            
            query = ""
            clean_keyword = ""

            if market == 'KR':
                clean_keyword = "한국 증시 시황"
                if subtype == 'OPENING': query = "오늘 한국 증시 개장 전망, 주요 일정, 리스크, 관전 포인트 분석"
                elif subtype == 'MID': query = "오늘 오전 한국 증시 상승 섹터, 하락 섹터, 특징주, 시황 요약"
                elif subtype == 'CLOSE': query = "오늘 한국 증시 마감 시황과 코스피 코스닥 등락 원인"
            
            elif market == 'US':
                clean_keyword = "US Stock Market News"
                if subtype == 'OPENING': query = "US stock market pre-market news and major economic events today. (Answer in Korean)"
                elif subtype == 'MID': query = "US stock market mid-day trading update and top gainers/losers. (Answer in Korean)"
                elif subtype == 'CLOSE': query = "US stock market closing summary and why major tech stocks moved today. (Answer in Korean)"
            
            print(f"🧠 [Gemini Pro] 요청: {query} (Mode: {pro_mode})")
            return await self.gemini_pro.search_and_summarize(query, link_keyword=clean_keyword, mode=pro_mode)
           
        return None

    async def run(self):
        """Main Loop: Redis 메시지 수신 대기"""
        print(f"🚀 [NewsWorker] 시스템 가동 완료 (Target: {getattr(settings, 'REDIS_CHANNEL_STOCK', 'stock_alert')})")
        
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        pubsub = r.pubsub()
        channel = getattr(settings, 'REDIS_CHANNEL_STOCK', 'stock_alert')
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data_str = message['data']
                    try:
                        data = ujson.loads(data_str)
                        msg_type = data.get('type')
                        
                        # 처리할 메시지 타입 필터링
                        if msg_type not in ['CONDITION', 'CONDITION_US', 'MARKET_BRIEFING']:
                            continue
                            
                        # ---------------------------------------------------
                        # 🧠 AI 분석 수행
                        # ---------------------------------------------------
                        final_result = await self.process_pipeline(data)
                        
                        if final_result:
                            # ✅ 분석 성공: 결과 전송
                            summary = final_result.get('summary', '')
                            
                            # 제목 설정 (종목명 or 브리핑 제목)
                            if msg_type == 'MARKET_BRIEFING':
                                mk_name = "🇰🇷 한국장" if data.get('market') == 'KR' else "🇺🇸 미국장"
                                sub_name = {"OPENING": "개장 브리핑", "MID": "오전/장중 브리핑", "CLOSE": "마감 브리핑"}.get(data.get('subtype'), "브리핑")
                                title = f"{mk_name} [{sub_name}]"
                            else:
                                title = data.get('name')
                            
                            payload = {
                                "type": "NEWS_SUMMARY",
                                "name": title,
                                "summary": summary,
                                "sentiment": final_result.get('sentiment', 'Neutral'),
                                "link": final_result.get('link', ''),
                                # ✅ [데이터 전달] 원본 메시지의 가격/등락률 정보 포함
                                "price": data.get('price'),
                                "rate": data.get('rate')
                            }
                            await r.publish("news_alert", ujson.dumps(payload))
                            print(f"✅ [발송 완료] {title} 분석 결과 Redis 전송됨")
                        else:
                            # 분석 실패 시 조용히 넘어감
                            print(f"   💨 [Skip] 유효한 뉴스/결과가 없어 전송하지 않습니다.")
                        
                    except Exception as e:
                        print(f"⚠️ [Error] 메시지 처리 중 오류: {e}")
                        
        except asyncio.CancelledError:
            print("🛑 NewsWorker 종료")
        finally:
            await r.aclose()