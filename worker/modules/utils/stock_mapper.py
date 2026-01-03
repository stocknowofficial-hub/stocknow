import FinanceDataReader as fdr

class StockMapper:
    _instance = None
    _krx_map = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StockMapper, cls).__new__(cls)
            cls._instance._load_data()
        return cls._instance

    def _load_data(self):
        print("📥 [System] 종목 데이터 매핑 준비...")
        
        # 1. [안전장치] 기본 수동 매핑을 먼저 정의합니다.
        # KRX 서버가 터져도 얘네들은 작동해야 하니까요.
        self._krx_map = {
            # 주요 국내 대형주
            "NAVER": "네이버",
            "035420": "네이버",
            "SAMSUNG ELECTRONICS": "삼성전자",
            "005930": "삼성전자",
            "SK HYNIX": "SK하이닉스",
            "000660": "SK하이닉스",
            "KAKAO": "카카오",
            "035720": "카카오",
            "HYBE": "하이브",
            "352820": "하이브",
            
            # 주요 해외 주식 (티커 -> 한글)
            "NVDA": "엔비디아",
            "TSLA": "테슬라",
            "AAPL": "애플",
            "MSFT": "마이크로소프트",
            "GOOGL": "구글",
            "AMZN": "아마존",
            "PLTR": "팔란티어",
            "AMD": "AMD"
        }

        # 2. KRX 전체 데이터 로딩 시도 (실패할 수 있음)
        try:
            # KRX 전체 종목 리스트 다운로드
            df = fdr.StockListing('KRX')
            
            # 받아온 데이터를 딕셔너리로 변환하여 기존 맵에 업데이트(덮어쓰기)
            # (수동 매핑이 덮어써지지 않게 순서를 조절하거나, KRX 데이터를 우선할지 결정)
            # 여기서는 KRX 데이터를 추가하는 방식으로 갑니다.
            krx_dict = dict(zip(df['Code'], df['Name']))
            
            # 가져온 KRX 데이터로 맵 확장 (기본 맵은 유지)
            # update를 쓰면 겹치는 키는 KRX 데이터로 덮어씌워짐
            # 우리는 수동 매핑(영어->한글)이 중요하므로, 역으로 병합하거나 그냥 둡니다.
            # 단순하게: KRX 데이터에 없는 것만 수동 맵에서 쓴다? -> 그냥 합치면 됩니다.
            
            # self._krx_map.update(krx_dict) # 이렇게 하면 코드로 찾을 때 이름 나옴
            
            # [팁] KRX 데이터는 "005930": "삼성전자" 형태입니다.
            # 우리는 "Code" -> "Name" 매핑이 필요하므로 추가합니다.
            for code, name in krx_dict.items():
                if code not in self._krx_map:
                    self._krx_map[code] = name
            
            print(f"✅ [System] KRX 데이터 연동 성공! (총 {len(self._krx_map)}개 종목)")
            
        except Exception as e:
            # 실패해도 괜찮음! 위에서 정의한 self._krx_map으로 돌아가면 됨.
            print(f"⚠️ [System] KRX 데이터 로딩 실패 (수동 매핑만 사용합니다): {e}")
            print(f"   👉 현재 사용 가능 종목: {list(self._krx_map.values())}")

    def get_korean_name(self, code_or_name):
        """
        입력: "005930" -> 출력: "삼성전자"
        입력: "NAVER" -> 출력: "네이버"
        """
        # 매핑된 게 있으면 반환, 없으면 입력값 그대로 반환
        return self._krx_map.get(code_or_name, code_or_name)