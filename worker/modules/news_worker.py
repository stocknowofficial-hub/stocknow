import asyncio
import ujson
import redis.asyncio as redis
from common.config import settings
from worker.modules.crawlers.naver import NaverCrawler
from worker.modules.crawlers.google import GoogleCrawler
from worker.modules.ai.analyst import AIAnalyst
from worker.modules.utils.stock_mapper import StockMapper

class NewsWorker:
    def __init__(self):
        self.naver = NaverCrawler()
        self.google = GoogleCrawler()
        self.ai = AIAnalyst()
        self.mapper = StockMapper()

    async def process_pipeline(self, keyword, market):
        search_keyword = self.mapper.get_korean_name(keyword)
        print(f"🔍 [통합 검색] '{keyword}' -> '{search_keyword}'")

        # 1. 최대한 많이 긁어오기 (네이버 4개 + 구글 4개)
        # (크롤러 코드에서는 display 숫자를 좀 늘려주세요)
        loop = asyncio.get_running_loop()
        task_naver = loop.run_in_executor(None, self.naver.search, search_keyword, 4) 
        task_google = loop.run_in_executor(None, self.google.search, search_keyword, market)
        
        naver_results, google_results = await asyncio.gather(task_naver, task_google)
        
        # 2. 데이터 구조화 (AI에게 넘길 포맷)
        # 단순 문자열 리스트가 아니라, {제목, 본문, 링크} 딕셔너리 리스트로 만듭니다.
        candidate_news = []

        def parse_raw_result(raw_list, source):
            parsed = []
            if not raw_list: return []
            for raw in raw_list:
                # 기존 크롤러가 "[소스] 제목\n본문\n(링크: ...)" 문자열을 줬다고 가정하고 파싱
                # (크롤러 코드를 수정해서 딕셔너리를 반환하게 하면 더 좋지만, 일단 문자열 파싱으로 처리)
                try:
                    parts = raw.split("\n")
                    title = parts[0]
                    # 본문은 중간 내용, 링크는 마지막 줄
                    link = parts[-1].replace("(링크: ", "").replace(")", "").strip()
                    body = "\n".join(parts[1:-1])
                    parsed.append({"source": source, "title": title, "body": body, "link": link})
                except:
                    continue
            return parsed

        candidate_news.extend(parse_raw_result(naver_results, "Naver"))
        candidate_news.extend(parse_raw_result(google_results, "Google"))

        if not candidate_news:
            print("   ❌ 뉴스 수집 실패 (0건)")
            return None, None

        print(f"🧠 [AI 심사] 총 {len(candidate_news)}개 기사 중 '진짜 원인' 선별 중...")
        
        # 3. AI 분석 요청 (리스트 통째로 전달)
        print(f"🧠 [AI 분석] 총 {len(candidate_news)}개 기사 채점 중...")
        result = await self.ai.analyze(search_keyword, candidate_news)
        
        # 4. 결과 매칭
        final_link = ""
        if result:
            best_idx = result.get("best_article_id", -1)
            
            # AI가 선택한 ID가 유효한지 확인
            if isinstance(best_idx, int) and 0 <= best_idx < len(candidate_news):
                selected_news = candidate_news[best_idx]
                final_link = selected_news['link']
                
                # 결과 딕셔너리에 'summary' 키가 'final_summary'로 올 수 있으니 매핑
                if 'final_summary' in result:
                    result['summary'] = result['final_summary']
                
                print(f"   🎯 최종 선정: [ID {best_idx}] {selected_news['title']}")
            else:
                return None, None
        else:
             # 점수 미달로 None이 리턴된 경우
             return None, None

        return result, final_link

    async def run(self):
        """Main Loop"""
        print(f"📰 [뉴스팀] 하이브리드 NewsWorker 가동! (Naver + Google)")
        
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        pubsub = r.pubsub()
        channel = getattr(settings, 'REDIS_CHANNEL_STOCK', 'stock_alert')
        await pubsub.subscribe(channel)

        print(f"👂 Redis 채널 '{channel}' 구독 중...")

        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data_str = message['data']
                    try:
                        data = ujson.loads(data_str)
                        if data.get('type') not in ['CONDITION', 'CONDITION_US']:
                            continue
                            
                        keyword = data.get('name')
                        market = data.get('market', 'KR')
                        
                        print(f"\n⚡ [신호 감지] {keyword} ({market})")
                        
                        # 파이프라인 실행
                        ai_result, link = await self.process_pipeline(keyword, market)
                        
                        if ai_result:
                            summary = ai_result.get('summary', '요약 없음')
                            if isinstance(summary, list): summary = "\n".join(summary)
                            
                            payload = {
                                "type": "NEWS_SUMMARY",
                                "name": keyword,
                                "summary": summary,
                                "sentiment": ai_result.get('sentiment', 'Neutral'),
                                "link": link
                            }
                            await r.publish("news_alert", ujson.dumps(payload))
                            print(f"✅ [발송 완료] {keyword} 분석 끝")
                        else:
                            print(f"   💨 분석 결과 없음 (뉴스 부족 등)")
                        
                    except Exception as e:
                        print(f"⚠️ Worker 에러: {e}")
                        
        except asyncio.CancelledError:
            print("🛑 NewsWorker 종료")
        finally:
            await r.aclose()