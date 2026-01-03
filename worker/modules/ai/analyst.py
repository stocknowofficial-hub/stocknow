import asyncio
import ujson
import requests

LOCAL_LLM_URL = "http://127.0.0.1:1234/v1/chat/completions"
LOCAL_MODEL_NAME = "qwen/qwen3-vl-8b" 

class AIAnalyst:
    def __init__(self):
        print(f"🧠 [AI팀] Analyst 준비 완료 (Scorecard 모드)")

    def _get_scorecard_prompt(self, stock_name, formatted_news_list):
        return f"""
        당신은 까다로운 주식 뉴스 편집장입니다.
        '{stock_name}'의 주가 변동 원인을 찾기 위해 아래 뉴스들을 평가해야 합니다.

        [뉴스 리스트]
        {formatted_news_list}

        [지시사항]
        1. 각 뉴스(ID)별로 **관련성 점수(0~100점)**를 매기십시오.
        2. 점수 기준:
           - **90~100점**: '{stock_name}'의 구체적인 호재/악재(공시, 계약, 실적, 인수합병)가 메인 주제임.
           - **50~80점**: '{stock_name}'가 언급되지만, 단순 시황이나 테마주 나열, 기대감 위주임.
           - **0~40점**: 광고, 전혀 다른 회사 이야기, 단순 주가 중계.
        3. 점수가 가장 높은 기사 하나를 선정하여 요약하십시오.
        4. **만약 80점 넘는 기사가 하나도 없다면, '관련 기사 없음'으로 판단하십시오.**

        [출력 형식 (JSON)]
        {{
            "evaluations": [
                {{"id": 0, "score": 20, "reason": "단순 마감 시황임"}},
                {{"id": 1, "score": 95, "reason": "삼성전자와의 공급 계약 체결 내용이 있음"}},
                ...
            ],
            "best_article_id": 1,  (없으면 -1)
            "final_summary": "선택한 기사의 3줄 핵심 요약 (한국어)",
            "sentiment": "Positive/Negative/Neutral"
        }}
        """

    def _parse_json(self, raw_text):
        try:
            text = raw_text.strip()
            # <think> 태그 제거 (생각하는 과정 로그 삭제)
            if "</think>" in text: text = text.split("</think>")[-1].strip()
            # 마크다운 제거
            if "```" in text:
                parts = text.split("```")
                for part in parts:
                    if "{" in part: 
                        text = part.replace("json", "").strip()
                        break
            
            # JSON 추출
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                return ujson.loads(text[start:end+1])
            return None
        except:
            return None

    async def analyze(self, stock_name, news_items):
        if not news_items: return None
        
        # 1. 뉴스 포맷팅 (토큰 절약을 위해 본문 길이 제한)
        formatted_text = ""
        for idx, item in enumerate(news_items):
            title = item.get('title', '')
            # 본문이 너무 길면 LLM이 앞부분 까먹음 -> 300자 제한
            body = item.get('body', '')[:300].replace("\n", " ") 
            formatted_text += f"[ID: {idx}] 제목: {title} / 내용: {body}\n"

        # 2. LLM 채점 시작
        payload = {
            "model": LOCAL_MODEL_NAME,
            "messages": [
                {"role": "system", "content": "You are a strict financial editor. Output JSON only."},
                {"role": "user", "content": self._get_scorecard_prompt(stock_name, formatted_text)}
            ],
            "temperature": 0.0, # 창의성 0% -> 냉정한 평가
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
                result_json = self._parse_json(content)
                
                if result_json:
                    best_id = result_json.get('best_article_id')
                    
                    # [검증 로직] LLM이 뽑은 1등의 점수가 진짜 80점이 넘는지 확인 (파이썬이 한 번 더 검사)
                    evals = result_json.get('evaluations', [])
                    best_score = 0
                    
                    for evaluation in evals:
                        if evaluation.get('id') == best_id:
                            best_score = evaluation.get('score', 0)
                            break
                    
                    print(f"🤖 [AI 채점] 1등 ID: {best_id} (점수: {best_score}점)")
                    
                    if best_score < 80:
                        print(f"   📉 점수 미달 ({best_score}점 < 80점). 전송하지 않습니다.")
                        return None
                    
                    return result_json
                
                return None
            else:
                print(f"⚠️ [AI 통신 실패] {res.status_code}")
                return None
        except Exception as e:
            print(f"❌ [AI Error] {e}")
            return None