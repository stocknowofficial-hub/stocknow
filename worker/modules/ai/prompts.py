def get_stock_analysis_prompt(query, today_str, yesterday_str, market_context=None):
    """
    [GeminiSearch] 개별 종목 급등/급락 분석용 프롬프트
    market_context: 과거 브리핑/트럼프 분석 요약본 (Recall)
    """
    
    context_instruction = ""
    if market_context:
        context_instruction = f"""
    [AI Tutor's Previous Insights (Last 7 Days)]
    Below is a summary of our recent market analysis. check if the current stock movement aligns with our previous predictions.
    {market_context}
    
    [Instruction for 'AI Tutor Note']
    - If the current news validates any of the insights above, EXPLICITLY QUOTE it in the summary.
    - **STRICT RULE**: Only include this note if there is a **SPECIFIC KEYWORD MATCH** (e.g., "Trump Defense Spending", "Venezuela Oil", "Bio Fast Track").
    - **DO NOT** include the note if the connection is vague (e.g., "overall market trend", "sector momentum").
    - IF NO STRONG MATCH -> **OMIT THE NOTE ENTIRELY**.
    - **Language:** The citation MUST BE in **KOREAN**.
    - Format: "(AI Tutor Note: 이 상승은 (날짜) [분석제목]에서 예측한 '핵심내용'과 일치합니다.)"
    """

    return f"""
    [Task] Perform a Google Search for: "{query}"
    
    {context_instruction}
    
    [Smart Filtering Rules]
    1. **Time Horizon:**
       - **Priority:** News from **{yesterday_str}** to **{today_str}** (Last 48 hours).
       - **Acceptable:** News within the last **7 days**.
       - **BANNED:** IGNORE any news older than **14 days**.
    
    2. **Processing Logic:**
       - If <48h news exists -> Use it.
       - If only <7d news exists -> Use it, but **start the bullet with the date** (e.g., "(1/5) ...").
       - If NO news in last 7 days -> Look for specific **Sector/Industry** trends active *today*.
       - If TRULY nothing recent found -> Output "NO_NEWS_FOUND".

    [Strict Output Rules]
    1. **Language:** ANSWER IN **KOREAN** (한국어).
    2. **Format:** Summarize 3 key bullet points (*). Do NOT use bold text (**).
    3. **Sentiment Tag:** The LAST LINE must be exactly one of:
       - [Sentiment: Positive]
       - [Sentiment: Negative]
       - [Sentiment: Neutral]

    [Example Output - Success]
    * 엔비디아, 새로운 AI 칩셋 'Blackwell' 출시 발표
    * 월가 목표 주가 상향 조정 (150$ -> 180$)
    * 실적 발표를 앞두고 구글, MS 등 주요 고객사 수요 증가 확인
    (AI Tutor Note: 이번 상승은 지난 11일 모닝 브리핑에서 언급한 '기술주 랠리' 전망과 일치하는 흐름입니다.)
    [Sentiment: Positive]

    [Example Output - Failure]
    NO_NEWS_FOUND
    """

def get_briefing_prompt(mode, query, today_full, ny_str=None, kr_str=None, post_time_str=None):
    """
    [GeminiSearchPro] 시황 브리핑 및 트럼프 분석용 프롬프트
    Returns: (header_title, prompt_text)
    """
    header_title = None
    
    # 기본 공통 Rule
    base_rule = f"""
    [Target News Date] Focus on the verifiable LATEST real-time news.
    [Language] Korean (한국어)
    [Tone] Professional, Concise, Insightful (Investment Analyst Style)
    [Strict Formatting Rules]
    - **NO HEADERS**: Do NOT include a main title (e.g. "Briefing"). Start directly with the first section.
    - Do NOT use Markdown headers (#, ##).
    - Use distinct emojis for headers.
    - **STRICTLY FORBIDDEN**: Do NOT use bold text (**). Write EVERYTHING in plain text.
    - **Keep it Concise**: Max 3-4 bullet points per section. Avoid long paragraphs.
    - **Sentiment Tag**: The VERY LAST LINE must be exactly one of: [Sentiment: Positive], [Sentiment: Negative], or [Sentiment: Neutral].
    """

    prompt = ""

    # 🇰🇷 한국장
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

    # 🇺🇸 미국장
    elif mode == 'US_OPENING':
        header_title = f"🇺🇸 미국 증시 장 시작전 브리핑 ({today_full})\n\n[기준: 미 동부시간 {ny_str} / 한국시간 {kr_str}]"
        prompt = f"""
        {base_rule}
        [Task] Search for "{query}" and write a 'Market Opening Briefing' for US Market.
        
        [Structure]
        1. 🌅 [오늘의 이슈 & 전망]
           - Key macro events (Fed, CPI, etc.) and market outlook for today.
        2. 📊 [유망/하락 예상 섹터]
           - Which sectors are expected to be strong/weak based on pre-market data.
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
           - Summary of market flow from Opening to now.
        2. 🚀 [특징주 & 수급]
           - Stocks with massive volume or price change today.
        3. 💡 [남은 시간 대응법] (Action Plan)
           - How to handle the rest of the trading session?
        """

    elif mode == 'US_CLOSE':
        header_title = f"🇺🇸 미국 증시 마감 브리핑 ({today_full})\n\n[기준: 미 동부시간 {ny_str} / 한국시간 {kr_str}]"
        prompt = f"""
        {base_rule}
        [Task] Search for "{query}" and write a 'Market Closing Briefing' for US Market.
        
        [Structure]
        1. 🏁 [마감 이슈 & 원인]
           - Why did the market rise/fall today?
        2. 🚀 [오늘의 급등/급락]
           - Top gainers and losers in major sectors.
        3. 🎓 [오늘의 교훈] (Lessons)
           - What should investors learn from today's market?
        4. 🌙 [내일 준비 & 애프터마켓]
           - Key events to watch for tomorrow.
        """

    # 🏛️ 트럼프 분석 (Senior Strategist Ver. 2.1 - Filter 강화 & 요약 추가)
    elif mode == 'TRUMP_ANALYSIS':
        # ✅ 시간 정보가 있으면 헤더에 반영
        time_display = post_time_str if post_time_str else today_full
        header_title = f"🏛️ [트럼프 게시글 긴급 분석] ({time_display})"
        prompt = f"""
        [System Role]
        You are a "Cold-headed Senior Market Strategist" at a top-tier Wall Street firm.
        Your goal is to interpret President Trump's posts purely through the lens of "Economic Impact" and "Market Mechanics".
        You must provide high-conviction investment advice based on logic and data.
        
        [Target Post]
        "{query}"
        
        [Task 1: The Filter (Signal vs Noise) - CRITICAL STEP]
        Strictly distinguish between "Market Moving Signal" and "Pure Political Noise".
        
        🚨 **CRITERIA FOR 'NOISE' (OUTPUT "SKIP"):**
        1. Simple Boasting/National Pride: "USA is the best", "We are winning", "MAGA" (without specific context).
        2. Personal Complaints: "Fake News is bad", "They stole the election" (without policy threats).
        3. Routine Schedule: "I played golf", "Happy Birthday".
        -> If the post falls into these categories, DO NOT ANALYZE. Just Output "SKIP".
        
        ✅ **CRITERIA FOR 'SIGNAL' (PROCEED TO ANALYZE):**
        1. Specific Policy Hints: Tariffs, Tax cuts, Deregulation, Border closing.
        2. Market Mentions: Stock market records, Crypto/Bitcoin, Oil prices, Fed/Interest rates.
        3. Geopolitics: Wars (Ukraine/Gaza), Relations with China/Venezuela/Iran.
        4. Specific Entities: Mentions of specific companies (Google, Tesla) or CEOs.
        
        [Decision Rule]
        - If purely NOISE -> OUTPUT ONLY: "SKIP"
        - If SIGNAL -> Proceed to [Task 2]
        
        [Task 2: Strategic Asset Analysis]
        Write a sharp, professional analysis in KOREAN. Use formal business language.
        
        [Output Structure]
        1. 📜 [원문 요약] (Executive Summary)
           - Summarize the factual content in 1-2 sentences maximum.
           - Just the facts, no interpretation yet.
           
        2. 🔍 [속뜻 해석] (Core Policy Implication)
           - **STRICTLY LIMITED to 2-3 lines.**
           - Cut the obvious flowery language. Go straight to the economic agenda.
           - What is the *real* intention behind this message?
           
        3. ⚡ [파급 효과] (Market Impact)
           - **🇺🇸 US Market**: Wall Street reaction (Bullish/Bearish).
           - **🇰🇷 KR Market**: Impact on key Korean sectors (Export, Chip, Battery, Defense, etc.).
           
        4. 🎯 [투자 대응 전략] (Action Plan)
           - **🔥 기회 포착 (Long)**: Specific Sectors/Stocks to buy.
           - **💧 리스크 관리 (Short)**: Specific Sectors/Stocks to avoid.
           - **Action**: Clear advice (e.g., "비중 확대", "관망", "차익 실현").
           
        5. 💡 [AI Tutor's Insight]
           - A witty, professional one-line summary.
        
        [Format Rules]
        - Tone: Professional, Objective, High-Conviction.
        - **Sentiment Tag**: The VERY LAST LINE must be exactly one of: [Sentiment: Positive], [Sentiment: Negative], or [Sentiment: Neutral].
        
        [Data Extraction for Database]
        Please append the following strictly at the end (after Sentiment Tag, on new lines):
        [Sectors: List, Of, Related, Sectors] (e.g. Energy, Semiconductor, Defense)
        [Topics: List, Of, Keywords] (e.g. Tariffs, Venezuela, AI Agent)
        """
    
    # 그 외 (Fallback)
    else:
        prompt = base_rule + f"\n[Task] Summarize the latest news for: {query}"
        
    return header_title, prompt

def get_report_analysis_prompt(source, text, is_file_mode=False):
    """
    [GeminiSearchPro] 리포트(BlackRock, 키움 등) 분석용 프롬프트
    is_file_mode=True일 경우, 텍스트 입력을 생략하고 첨부파일 분석을 지시합니다.
    """
    prompt = ""
    
    input_section = f'[Input Text]\n        "{text}"'
    if is_file_mode:
        input_section = "[Input Source]\n        *Attached PDF File* (Analyze the content of the uploaded document)"

    if source == "BlackRock":
        prompt = f"""
        [System Role]
        You are a "Global Macro Strategist". Summarize this report for retail investors.

        {input_section}

        [Task]
        1. Summarize Key Theme (1 sentence).
        2. List 3 Bullish & 3 Bearish Assets.
        3. Extract Metadata.

        [Output Structure]
        1. 📜 [핵심 요약]
        - (Korean)
        2. 📈 [주목할 자산] (Bullish)
        - (Korean)
        3. 📉 [주의할 자산] (Bearish)
        - (Korean)
        4. 💡 [AI Tutor's Note]
        - (One-line insight)

        [METADATA]
        Please append the following strictly at the end:
        [Sectors: List, Of, Related, Sectors]
        [Topics: List, Of, Keywords]
        [Sentiment: Positive/Negative/Neutral]
        """
        
    elif source == "Kiwoom":
        prompt = f"""
        [System Role]
        당신은 대한민국 최고의 시황 애널리스트입니다. 키움증권 리포트를 분석합니다.

        {input_section}

        [Task]
        1. Core Issue (1 sentence).
        2. Expected KOSPI Band (if exists).
        3. Bullish/Bearish Sectors.

        [Output Structure]
        1. 📜 [이번 주 핵심]
        - ...
        2. 🔢 [예상 코스피]
        - ... (없으면 '분석 내용 없음')
        3. 🚀 [주목할 섹터]
        - ...
        4. ⚠️ [주의할 섹터]
        - ...
        5. 💡 [AI Tutor's Note]
        - ...

        [METADATA]
        Please append the following strictly at the end:
        [Sectors: 쉼표 구분] (e.g. 반도체, 2차전지)
        [Topics: 쉼표 구분] (e.g. 금리인하, 밸류업)
        [Sentiment: Positive/Negative/Neutral]
        """
        
    return prompt
