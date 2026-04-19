def get_stock_analysis_prompt(query, today_str, yesterday_str, market_context=None, rate=None):
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
    - If the current news validates any of the insights above, EXPLICITLY QUOTE it.
    - **STRICT RULE**: Only include this note if there is a **SPECIFIC KEYWORD MATCH** (e.g., "Trump Defense Spending", "Iran Ceasefire").
    - **DO NOT** include the note if the connection is vague.
    - IF NO STRONG MATCH -> **OMIT THE NOTE ENTIRELY**.
    - **Language:** The citation MUST BE in **KOREAN**.
    - **Format:** "🎯 **[인사이트 적중]** (날짜) 브리핑에서 짚어드린 '(핵심내용)' 모멘텀이 정확히 시장에 반영되었습니다."
    """

    # 실제 등락률 주입 (Search Grounding 실패 시 할루시네이션 방지)
    rate_block = ""
    if rate is not None:
        try:
            rate_val = float(rate)
            direction = "상승" if rate_val > 0 else "하락"
            rate_block = f"""
    [VERIFIED MARKET DATA — ABSOLUTE TRUTH]
    - 현재 등락률: {rate_val:+.2f}% ({direction})
    - 이 수치는 확인된 실제 데이터입니다. 검색 결과와 무관하게 반드시 이 방향에 맞게 분석하세요.
    - [투자 판단]의 이모지와 방향은 반드시 이 등락률과 일치해야 합니다.
    """
        except:
            pass

    return f"""
    [Task] Perform a Google Search for: "{query}"

    {rate_block}
    {context_instruction}

    [Smart Filtering Rules]
    1. **Time Horizon:** Priority: News from **{yesterday_str}** to **{today_str}** (Last 48 hours). BANNED: Older than 14 days.
    2. **Processing Logic:**
       - If <48h news exists -> Use it.
       - If only <7d news exists -> Use it, but **start the bullet with the date** (e.g., "(4/10) ...").
       - If no recent news -> Look for specific **Sector/Industry** trends active today.
       - If TRULY nothing found -> Output "NO_NEWS_FOUND".

    [Strict Output Rules]
    1. **Language:** ANSWER IN **KOREAN** (한국어). Tone must be sharp, professional, and concise (Trader style).
    2. **Format:** EXACTLY 2 Bullet Points.
       * Point 1: **[핵심 원인]** - Explain WHY it is moving using specific facts and numbers (e.g., contract size, target price).
         - **CRITICAL:** Do NOT write "The stock is rising/falling because...". Just state the trigger facts directly.
         - Keep sentences short and punchy.
       * Point 2: **[투자 판단]** - Start with an emoji: 🐂 (Positive/Buy), 🐻 (Negative/Sell), ⚖️ (Neutral/Hold).
         - Provide one sentence of actionable advice (e.g., "단기 과열 주의. 추격 매수 자제", "수급 유입 지속으로 추가 상승 여력 충분").
    3. **Sentiment Tag:** The LAST LINE must be exactly one of: [Sentiment: Positive], [Sentiment: Negative], or [Sentiment: Neutral].

    [Example Output - Success]
    * [핵심 원인] 체코 신규 원전 2기 우선협상대상자 선정 등 24조 원 규모 수주 기대감. 2분기 영업이익 15% 상향 조정 리포트 발간이 투심을 자극함.
    * [투자 판단] 🐂 **긍정** (외국인과 기관의 양매수 수급이 강력하게 유입 중. 추가 모멘텀 유효)
    🎯 **[인사이트 적중]** 4/8 브리핑에서 짚어드린 '체코 원전 수주전 훈풍' 모멘텀이 정확히 시장에 반영되었습니다.
    [Sentiment: Positive]

    [Example Output - Failure]
    NO_NEWS_FOUND
    """

def get_briefing_prompt(mode, query, today_full, ny_str=None, kr_str=None, post_time_str=None, market_data=None):
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
    - **Data-Driven (CRITICAL)**: You MUST include specific numbers (%, prices, indices) and EXACT company names/tickers. Do not say "Tech rose". Say "Nvidia (+2.5%) led the tech rally".
    - **NO HALLUCINATION (ABSOLUTE RULE)**: Exchange rates (원/달러), KOSPI/KOSDAQ levels, US index levels, Oil prices, Bond yields — ALL numeric values MUST come directly from search results. NEVER generate or guess numbers from memory. If you cannot find the exact number in search results, write 'N/A' instead.
    - **Sentiment Tag**: The VERY LAST LINE must be exactly one of: [Sentiment: Positive], [Sentiment: Negative], or [Sentiment: Neutral].
    """

    prompt = ""

    # 🇰🇷 한국장
    if mode == 'KR_OPENING':
        header_title = f"🇰🇷 한국 증시 장 시작전 브리핑 ({today_full})"

        # 검증된 시장 데이터 주입 블록
        verified_data_block = ""
        if market_data:
            lines = ["[VERIFIED MARKET DATA — API에서 직접 조회한 확정 수치입니다]",
                     "아래 수치를 분석의 기반으로 반드시 사용하세요. 절대 다른 수치로 바꾸거나 모순된 분석을 쓰지 마세요."]
            for key, val in market_data.items():
                lines.append(f"- {key}: {val}")
            lines.append("[END OF VERIFIED DATA]")
            verified_data_block = "\n        ".join(lines)

        prompt = f"""
        {base_rule}
        {verified_data_block}

        [Task] Search for "{query}" and write a 'Market Opening Briefing' for Korea.

        [Structure]
        1. 📅 [오늘의 일정]
           - Key economic events, earnings releases, or policy announcements today.
        2. 📈 [시장 전망]
           - Expected market flow based on overnight US market. Use the VERIFIED DATA above for index numbers.
        3. ⚠️ [리스크 및 변수]
           - Negative factors, exchange rate risks, or geopolitical issues. Use VERIFIED DATA for exchange rate and oil price.
        4. 🧐 [관전 포인트]
           - Sectors or themes to watch closely today. Must mention at least 1-2 specific leading stocks (대장주).
        """

    elif mode == 'KR_MID':
        header_title = f"🇰🇷 한국 증시 장중 브리핑 ({today_full})"

        # 검증된 장중 지수 주입 블록
        verified_data_block = ""
        if market_data:
            lines = ["[VERIFIED MARKET DATA — API에서 직접 조회한 확정 수치입니다]",
                     "아래 코스피/코스닥/환율 수치는 실시간 API 값입니다. 반드시 이 수치를 사용하세요."]
            for key, val in market_data.items():
                lines.append(f"- {key}: {val}")
            lines.append("[END OF VERIFIED DATA]")
            verified_data_block = "\n        ".join(lines)

        prompt = f"""
        {base_rule}
        {verified_data_block}

        [Task] Search for "{query}" and write a 'Mid-Day Market Briefing' for Korea.

        [CRITICAL DATE VERIFICATION — ABSOLUTE RULE]
        - Every single stock movement, index level, and price MUST be from TODAY's live session only.
        - **FORBIDDEN**: Do NOT use any data from yesterday, last week, or any other date.
        - Before mentioning ANY individual stock's % change, verify the search result is from TODAY's trading session.
        - If you cannot confirm a stock's movement is from TODAY, OMIT that stock entirely. Do NOT guess.
        - "장 마감", "전일 대비", "전날" in search results = OLD DATA. SKIP IT.

        [Structure]
        1. 📈 [오전 상승 주도]
           - Top performing sectors/themes and WHY. Name the specific leading stocks.
        2. 📉 [오전 약세 흐름]
           - Weak sectors and reasons. Name the specific lagging stocks.
        3. 🚀 [특징주 코멘트]
           - Individual stocks with significant news/movement (Top 2-3). Must include exact % change.
        4. 📝 [장중 시황 요약]
           - Summary of KOSPI/KOSDAQ exact levels and Foreigner/Institution supply status (with numbers).
        """

    elif mode == 'KR_CLOSE':
        header_title = f"🇰🇷 한국 증시 마감 브리핑 ({today_full})"
        prompt = f"""
        {base_rule}
        [Task] Search for "{query}" and write a 'Market Closing Briefing' for Korea.

        [Structure]
        1. 🏁 [마감 총평]
           - KOSPI/KOSDAQ closing exact levels, % change, and main drivers.
        2. 🏆 [오늘의 승자/패자]
           - Best/Worst performing sectors. Must mention specific company names that drove the sector.
        3. 💡 [내일의 투자 아이디어]
           - Based on today's flow, name 1-2 specific themes/stocks to prepare for tomorrow.
        """

    # 🇺🇸 미국장
    elif mode == 'US_OPENING':
        header_title = f"🇺🇸 미국 증시 장 시작전 브리핑 ({today_full})\n\n[기준: 미 동부시간 {ny_str} / 한국시간 {kr_str}]"
        prompt = f"""
        {base_rule}
        [Task] Search for "{query}" and write a 'Market Opening Briefing' for US Market.

        [Structure]
        1. 🌅 [오늘의 이슈 & 전망]
           - Key macro events (Fed, CPI etc. with expected %).
        2. 📊 [유망/하락 예상 섹터]
           - Expected strong/weak sectors. Must name specific pre-market moving stocks/tickers.
        3. ⚠️ [투자자 유의사항]
           - Volatility risks, Bond yields (exact %), or specific stock warnings.
        4. 💡 [장초반 대응 전략] (Action Plan)
           - Practical advice with specific targets (e.g., "Focus on AI hardware like NVDA, AMD").
        """

    elif mode == 'US_MID':
        header_title = f"🇺🇸 미국 증시 장중 브리핑 ({today_full})\n\n[기준: 미 동부시간 {ny_str} / 한국시간 {kr_str}]"
        prompt = f"""
        {base_rule}
        [Task] Search for "{query}" and write a 'Mid-Day Briefing' for US Market.

        [Structure]
        1. 📝 [오전장 요약]
           - Major index flows with current exact % changes.
        2. 🚀 [특징주 & 수급]
           - Stocks with massive volume/price change. Must include Tickers and exact % changes.
        3. 💡 [남은 시간 대응법] (Action Plan)
           - Actionable advice naming specific sectors or ETFs to watch.
        """

    elif mode == 'US_CLOSE':
        header_title = f"🇺🇸 미국 증시 마감 브리핑 ({today_full})\n\n[기준: 미 동부시간 {ny_str} / 한국시간 {kr_str}]"
        prompt = f"""
        {base_rule}
        [Task] Search for "{query}" and write a 'Market Closing Briefing' for US Market.

        [Structure]
        1. 🏁 [마감 이슈 & 원인]
           - Major index closing numbers and exact % changes. The core reason for the move.
        2. 🚀 [오늘의 급등/급락]
           - Top gainers and losers. Must include specific Tickers and exact % changes.
        3. 🎓 [오늘의 교훈] (Lessons)
           - What should investors learn from today's market?
        4. 🌙 [내일 준비 & 애프터마켓]
           - Key events for tomorrow or significant after-market movers (with exact %).
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
        4. **Domestic Politics (Endorsements/Personal Attacks):**
           - Posts purely praising (Endorsement) OR attacking (Corruption/Embezzlement) specific individuals (Governors/Senators/Judges).
           - **SKIP** unless there is a **Direct Link to Federal Policy** (e.g. Tariffs, Federal Funding Cuts, Executive Orders).
           - Mere repetition of slogans or vague threats ("We want money back") are **NOISE**.
        -> If the post falls into these categories, DO NOT ANALYZE. Just Output "SKIP".
        
        ✅ **CRITERIA FOR 'SIGNAL' (PROCEED TO ANALYZE):**
        1. Specific Policy Hints: Tariffs, Tax cuts, Deregulation, Border closing.
        2. Market Mentions: Stock market records, Crypto/Bitcoin, Oil prices, Fed/Interest rates.
        3. Geopolitics: Wars (Ukraine/Gaza), Relations with China/Venezuela/Iran.
        4. Specific Entities: Mentions of specific companies (Google, Tesla) or CEOs.
        
        [Decision Rule]
        - If purely NOISE -> OUTPUT ONLY: "SKIP"
        - If SIGNAL -> Write the analysis below. Do NOT output "Task 1", "Task 2", "결정: SIGNAL" or any internal prompt labels. Start directly with the numbered sections.

        [Output Structure]
        Write a sharp, professional analysis in KOREAN. Use formal business language.
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
           
        5. 💡 [Stock Now's Insight]
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
    input_section = f'[Input Text]\n        "{text}"'
    if is_file_mode:
        input_section = "[Input Source]\n        *Attached PDF File* (Analyze the content of the uploaded document)"

    # source 정규화: 한국어 증권사명 → 내부 키로 매핑
    src = (source or "").strip()
    if src == "BlackRock":
        source_key = "BlackRock"
    elif any(k in src for k in ["키움", "Kiwoom"]):
        source_key = "Kiwoom"
    elif any(k in src for k in ["미래에셋", "MiraeAsset", "Mirae"]):
        source_key = "MiraeAsset"
    elif any(k in src for k in ["삼성", "Samsung"]):
        source_key = "Samsung"
    elif any(k in src for k in ["NH", "농협"]):
        source_key = "NH"
    elif any(k in src for k in ["한국투자", "Korea Investment"]):
        source_key = "KoreaInvestment"
    elif any(k in src for k in ["신한", "Shinhan"]):
        source_key = "Shinhan"
    elif any(k in src for k in ["하나", "Hana"]):
        source_key = "Hana"
    elif any(k in src for k in ["KB", "국민"]):
        source_key = "KB"
    else:
        source_key = "KR_BROKER"  # 기타 한국 증권사 공통 fallback

    METADATA_KR = """
        [METADATA]
        반드시 맨 마지막에 아래 형식으로 추가:
        [Sectors: 쉼표 구분] (예: 반도체, 2차전지, 바이오)
        [Topics: 쉼표 구분] (예: 금리인하, 밸류업, AI)
        [Sentiment: Positive/Negative/Neutral]
        """

    if source_key == "BlackRock":
        return f"""
        [System Role]
        You are a "Global Macro Strategist". Summarize this report for retail investors in KOREAN.

        {input_section}

        [Task]
        1. Summarize Key Theme (1 sentence).
        2. List 3 Bullish & 3 Bearish Assets.
        3. Extract Metadata.

        [Output Structure]
        1. 📜 [핵심 요약]
        - (한국어로 작성)
        2. 📈 [주목할 자산] (Bullish)
        - (한국어로 작성)
        3. 📉 [주의할 자산] (Bearish)
        - (한국어로 작성)
        4. 💡 [Stock Now's Note]
        - (한 줄 인사이트, 한국어)

        [METADATA]
        Please append strictly at the end:
        [Sectors: List, Of, Related, Sectors]
        [Topics: List, Of, Keywords]
        [Sentiment: Positive/Negative/Neutral]
        """

    elif source_key == "Kiwoom":
        return f"""
        [System Role]
        당신은 대한민국 최고의 시황 애널리스트입니다. 키움증권 주간 리포트를 분석합니다.
        반드시 한국어로 작성하세요.

        {input_section}

        [Task]
        1. 이번 주 핵심 이슈 1문장 요약.
        2. 예상 코스피 밴드 (있을 경우).
        3. 주목할 섹터 / 주의할 섹터.

        [Output Structure]
        1. 📜 [이번 주 핵심]
        - ...
        2. 🔢 [예상 코스피 밴드]
        - ... (언급 없으면 '해당 없음')
        3. 🚀 [주목할 섹터]
        - ...
        4. ⚠️ [주의할 섹터]
        - ...
        5. 💡 [Stock Now's Note]
        - ...
        {METADATA_KR}
        """

    elif source_key == "MiraeAsset":
        return f"""
        [System Role]
        당신은 대한민국 최고의 투자 애널리스트입니다. 미래에셋증권 리포트를 분석합니다.
        반드시 한국어로 작성하세요.

        {input_section}

        [Task]
        1. 리포트 핵심 주제 1문장.
        2. 주요 투자 포인트 (Bullish/Bearish 자산 또는 섹터).
        3. 리스크 요인.

        [Output Structure]
        1. 📜 [핵심 요약]
        - ...
        2. 📈 [투자 기회]
        - ...
        3. 📉 [리스크 요인]
        - ...
        4. 💡 [Stock Now's Note]
        - ...
        {METADATA_KR}
        """

    else:
        # 기타 한국 증권사 공통 fallback
        return f"""
        [System Role]
        당신은 대한민국 최고의 투자 애널리스트입니다. {src} 주간 리포트를 분석합니다.
        반드시 한국어로 작성하세요.

        {input_section}

        [Task]
        1. 리포트 핵심 주제 1문장 요약.
        2. 주목할 자산/섹터 (Bullish).
        3. 주의할 자산/섹터 (Bearish).
        4. 투자자를 위한 핵심 메시지.

        [Output Structure]
        1. 📜 [핵심 요약]
        - ...
        2. 📈 [주목할 자산/섹터]
        - ...
        3. 📉 [주의할 자산/섹터]
        - ...
        4. 💡 [Stock Now's Note]
        - ...
        {METADATA_KR}
        """
