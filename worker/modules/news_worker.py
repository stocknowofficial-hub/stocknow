import asyncio
import ujson
import redis.asyncio as redis
import pytz 
import aiohttp # ✅ Added for DB logging
from datetime import datetime
from common.config import settings
from common.logger import setup_logger # ✅ Logger Import
from worker.modules.ai.gemini_search import GeminiSearch
from worker.modules.ai.gemini_search_pro import GeminiSearchPro

logger = setup_logger("NewsWorker", "logs/worker", "worker.log")

class NewsWorker:
    def __init__(self):
        logger.info(f"📰 [NewsWorker] Dual Engine Mode (Flash=Stocks, Pro=Briefing)")
        self.gemini = GeminiSearch()           # 속도 (종목 분석용)
        self.gemini_pro = GeminiSearchPro()    # 지능 (시황 브리핑용)

    async def fetch_recent_context(self):
        """백엔드에서 최근 분석 로그(7일치)를 가져와서 문자열로 변환"""
        try:
            async with aiohttp.ClientSession() as session:
                # 📉 [Cost Optimization] 7일 -> 3일로 축소 (토큰 절약)
                async with session.get(f"{settings.BACKEND_URL}/analysis/market/recent?days=3") as resp:
                    if resp.status == 200:
                        logs = await resp.json()
                        if not logs: return None
                        
                        context_lines = []
                        for idx, log in enumerate(logs):
                            # [트럼프분석] (2026-01-11) "블라블라..." (Sectors: Energy)
                            meta = ""
                            if log.get('sectors'): meta += f" [Sectors: {log['sectors']}]"
                            
                            line = f"{idx+1}. ({log['date']}) [{log['category']}] \"{log['title']}\"{meta}\n   - 요약: {log['summary'][:100]}..."
                            context_lines.append(line)
                            
                        return "\n".join(context_lines)
        except Exception as e:
            logger.error(f"⚠️ [Context] 과거 기록 조회 실패: {e}")
        return None

    async def save_to_db(self, category, title, content, sentiment, related_code, price_info):
        """백엔드 API로 분석 결과 전송"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "category": category,
                    "title": title,
                    "content": content,
                    "sentiment": sentiment,
                    "related_code": related_code,
                    "price_info": price_info
                }
                async with session.post(f"{settings.BACKEND_URL}/analysis", json=payload) as resp:
                    if resp.status == 200:
                        logger.info(f"💾 [DB Saved] {title} 분석 기록 저장 완료")
                    else:
                        logger.error(f"⚠️ [DB Error] 저장 실패: {resp.status} - {await resp.text()}")
        except Exception as e:
            logger.error(f"⚠️ [DB Error] 연결 실패: {e}")

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
        date_str_kr = now_kr.strftime("%Y년 %m월 %d일") 

        # 2. 미국 뉴욕 시간 (API 검색용)
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        
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

            # 🇰🇷 [한국장 전략] 
            if market == 'KR':
                move_type = "급등" if is_bullish else "급락"
                query = f"{name} {move_type} 이유 및 관련 최신 뉴스 (주가 전망 포함)"
                clean_keyword = name 

            # 🇺🇸 [미국장 전략]
            else:
                clean_keyword = f"{code} stock"
                search_subject = f"{name} ({code})"
                
                if is_bullish:
                    query = f"Why is {search_subject} stock up today? latest news and analyst rating. (Answer in Korean)"
                else:
                    query = f"Why is {search_subject} stock down today? latest news and major issues. (Answer in Korean)"
            
            # ✅ [Context Injection] 최근 분석 기록(트럼프/브리핑) 가져오기
            market_context = await self.fetch_recent_context()
            
            print(f"🧠 [Gemini 요청] {query} / [Link] {clean_keyword}")
            if market_context: logger.info(f"   ㄴ 📚 Context Injected: {len(market_context)} chars")
            
            return await self.gemini.search_and_summarize(query, link_keyword=clean_keyword, market_context=market_context)

        # -----------------------------------------------------
        # E. 고래 포착 (WHALE_ALERT) - AI Bypass
        # -----------------------------------------------------
        elif msg_type == 'WHALE_ALERT':
            name = msg_data.get('name')
            # 📉 [Cost Optimization] AI Bypass
            logger.info(f"🐋 [Whale] {name} 고래 포착 (AI 분석 생략)")
            return {
                "summary": "AI Analysis Skipped",
                "sentiment": "Neutral",
                "link": f"https://finance.yahoo.com/quote/{msg_data.get('code')}"
            }

        # -----------------------------------------------------
        # F. K-Whale (국내 수급 포착) - AI Bypass
        # -----------------------------------------------------
        elif msg_type == 'K_WHALE_ALERT':
            name = msg_data.get('name')
            # 📉 [Cost Optimization] AI Bypass
            logger.info(f"🐳 [K-Whale] {name} 국내 수급 포착 (AI 분석 생략)")
            return {
                "summary": "AI Analysis Skipped",
                "sentiment": "Neutral",
                "link": f"https://finance.naver.com/item/main.naver?code={msg_data.get('code')}"
            }

        # -----------------------------------------------------
        # B. 시황 브리핑 (MARKET_BRIEFING)
        # -----------------------------------------------------
        elif msg_type == 'MARKET_BRIEFING':
            subtype = msg_data.get('subtype') 
            pro_mode = f"{market}_{subtype}"
            
            query = ""
            clean_keyword = ""

            if market == 'KR':
                clean_keyword = "한국 증시"
                if subtype == 'OPENING': query = "오늘 한국 증시 개장 전망, 주요 일정, 리스크, 관전 포인트 분석"
                elif subtype == 'MID': query = "오늘 오전 한국 증시 상승 섹터, 하락 섹터, 특징주, 시황 요약"
                elif subtype == 'CLOSE': query = "오늘 한국 증시 마감 시황과 코스피 코스닥 등락 원인"
            
            elif market == 'US':
                clean_keyword = "US Stock Market News"
                if subtype == 'OPENING': query = "US stock market pre-market news and major economic events today. (Answer in Korean)"
                elif subtype == 'MID': query = "US stock market mid-day trading update and top gainers/losers. (Answer in Korean)"
                elif subtype == 'CLOSE': query = "US stock market closing summary and why major tech stocks moved today. (Answer in Korean)"
            
            logger.info(f"🧠 [Gemini Pro] 요청: {query} (Mode: {pro_mode})")
            return await self.gemini_pro.search_and_summarize(query, link_keyword=clean_keyword, mode=pro_mode)

        # -----------------------------------------------------
        # C. SNS 분석 (SNS_ANALYSIS) - 트럼프 전담
        # -----------------------------------------------------
        elif msg_type == 'SNS_ANALYSIS':
            author = msg_data.get('author', 'Unknown')
            text = msg_data.get('text', '')
            original_url = msg_data.get('url', '')
            post_time = msg_data.get('time') # ✅ 시간 정보 추출
            
            query = text
        # D. 주간 리포트 분석 (REPORT_ANALYSIS)
        # -----------------------------------------------------
        elif msg_type == 'REPORT_ANALYSIS':
            source = msg_data.get('source')
            title = msg_data.get('title')
            text = msg_data.get('text')
            file_path = msg_data.get('file_path') # ✅ File Path Check
            
            logger.info(f"📑 [Report Analysis] {source}: {title}")
            
            if file_path:
                logger.info(f"   ㄴ 📂 File Mode: {file_path}")
                return await self.gemini_pro.analyze_report_file(source, title, file_path)
            else:
                return await self.gemini_pro.analyze_report(source, title, text)
           
        return None

    async def run(self, shutdown_event=None):
        """Main Loop: Redis 메시지 수신 대기 (Manual Polling)"""
        logger.info(f"🚀 [NewsWorker] 시스템 가동 완료 (Target: {getattr(settings, 'REDIS_CHANNEL_STOCK', 'stock_alert')})")
        
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True)
        
        try:
             # ✅ Use Async Context Manager
            async with r.pubsub() as pubsub:
                channel_stock = getattr(settings, 'REDIS_CHANNEL_STOCK', 'stock_alert')
                # ✅ Subscribe to both Stock Alerts and Whale Alerts
                await pubsub.subscribe(channel_stock, "whale_alert")

                # ✅ Manual Polling Loop (No GeneratorExit Issues)
                while True:
                    if shutdown_event and shutdown_event.is_set():
                        break

                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message:
                        if message['type'] == 'message':
                            data_str = message['data']
                            try:
                                data = ujson.loads(data_str)
                                
                                msg_type = data.get('type')
                                
                                if msg_type not in ['CONDITION', 'CONDITION_US', 'MARKET_BRIEFING', 'SNS_ANALYSIS', 'REPORT_ANALYSIS', 'WHALE_ALERT', 'K_WHALE_ALERT']:
                                    pass # continue equivalent
                                else:
                                    # 🧠 AI 분석 수행
                                    final_result = await self.process_pipeline(data)
                                    
                                    if final_result:
                                        summary = final_result.get('summary', '')

                                        if "SKIP" in summary:
                                            logger.info(f"🔇 [AI Filter] 영양가 없는 잡담으로 판별됨. (Skip)")
                                        else:
                                            # 제목 및 카테고리 설정
                                            category = "STOCK"
                                            if msg_type == 'MARKET_BRIEFING':
                                                mk_name = "🇰🇷 한국장" if data.get('market') == 'KR' else "🇺🇸 미국장"
                                                sub_name = {"OPENING": "개장 브리핑", "MID": "오전/장중 브리핑", "CLOSE": "마감 브리핑"}.get(data.get('subtype'), "브리핑")
                                                title = f"{mk_name} [{sub_name}]"
                                                category = "BRIEFING"
                                            elif msg_type == 'SNS_ANALYSIS':
                                                title = f"🏛️ [트럼프 긴급 포착]"
                                                category = "TRUMP"
                                            elif msg_type == 'REPORT_ANALYSIS':
                                                mk_source = data.get('source', 'Analyst')
                                                title = f"📑 [{mk_source} 리포트 Output]"
                                                category = "ANALYST_REPORT"
                                            elif msg_type == 'WHALE_ALERT':
                                                title = f"🐳 [Whale] {data.get('name')}"
                                                category = "WHALE"
                                            elif msg_type == 'K_WHALE_ALERT':
                                                title = f"🐳 [K-Whale] {data.get('name')}"
                                                category = "WHALE"
                                            else:
                                                title = data.get('name')
                                                category = "STOCK"
                                                
                                            # ✅ Payload Link Logic (Compute BEFORE Saving DB)
                                            final_link = final_result.get('link', '')
                                            if msg_type == 'REPORT_ANALYSIS' and data.get('url'):
                                                final_link = data.get('url') # Override with Real PDF URL

                                            # ✅ [DB Save] 분석 결과 백엔드로 전송 (Split)
                                            if category == "STOCK":
                                                await self.save_stock_log(
                                                    code=data.get('code'),
                                                    name=data.get('name'),
                                                    price=str(data.get('price', '')),
                                                    rate=str(data.get('rate', '')),
                                                    summary=summary,
                                                    sentiment=final_result.get('sentiment', 'Neutral')
                                                )
                                            else:
                                                await self.save_market_log(
                                                    category=category,
                                                    title=title,
                                                    content=summary,
                                                    sentiment=final_result.get('sentiment', 'Neutral'),
                                                    original_url=final_link, # ✅ Use Correct Link
                                                    sectors=final_result.get('sectors'),
                                                    topics=final_result.get('topics')
                                                )
                                            
                                            payload = {
                                                "type": "SNS_SUMMARY" if msg_type == 'SNS_ANALYSIS' else "NEWS_SUMMARY",
                                                "name": title,
                                                "summary": summary,
                                                "sentiment": final_result.get('sentiment', 'Neutral'),
                                                "link": final_link, 
                                                "price": data.get('price'),
                                                "rate": data.get('rate')
                                            }

                                            # WHALE_ALERT인 경우 type 변경
                                            if msg_type == 'WHALE_ALERT':
                                                payload["type"] = "WHALE_SUMMARY"
                                                payload["extra_info"] = {
                                                    "big_tick_count": data.get('big_tick_count'),
                                                    "threshold": data.get('threshold')
                                                }
                                            elif msg_type == 'K_WHALE_ALERT':
                                                payload["type"] = "K_WHALE_SUMMARY"
                                                payload["extra_info"] = {
                                                    "program_delta": data.get('program_delta'),
                                                    "program_total": data.get('program_total'),
                                                    "foreign_delta": data.get('foreign_delta'),
                                                    "foreign_total": data.get('foreign_total')
                                                }
                                            
                                            if msg_type == 'SNS_ANALYSIS':
                                                pass
                                            await r.publish("news_alert", ujson.dumps(payload))
                                            logger.info(f"✅ [발송 완료] {title} 분석 결과 Redis 전송됨")
                                    else:
                                        logger.info(f"   💨 [Skip] 유효한 뉴스/결과가 없어 전송하지 않습니다.")
                            
                            except Exception as e:
                                logger.error(f"⚠️ [Error] 메시지 처리 중 오류: {e}")
                    
                    # Loop delay
                    await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            logger.info("🛑 NewsWorker 종료")
        finally:
            await r.aclose()

    async def save_stock_log(self, code, name, price, rate, summary, sentiment):
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"code": code, "name": name, "price": price, "rate": rate, "summary": summary, "sentiment": sentiment}
                async with session.post(f"{settings.BACKEND_URL}/analysis/stock", json=payload) as resp:
                    if resp.status != 200: logger.error(f"⚠️ [DB Error] Stock 저장 실패: {await resp.text()}")
        except Exception as e: logger.error(f"⚠️ [DB Error] Stock 연결 실패: {e}")

    async def save_market_log(self, category, title, content, sentiment, original_url, sectors=None, topics=None):
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "category": category, 
                    "title": title, 
                    "content": content, 
                    "sentiment": sentiment, 
                    "original_url": original_url,
                    "sectors": sectors, # ✅ New
                    "topics": topics    # ✅ New
                }
                async with session.post(f"{settings.BACKEND_URL}/analysis/market", json=payload) as resp:
                    if resp.status != 200: logger.error(f"⚠️ [DB Error] Market 저장 실패: {await resp.text()}")
        except Exception as e: logger.error(f"⚠️ [DB Error] Market 연결 실패: {e}")