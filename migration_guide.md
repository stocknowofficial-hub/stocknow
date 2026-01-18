# 🍎 Windows -> MacBook (Docker) 이관 및 운영 가이드

사장님, 이제 발열 심한 윈도우에서 벗어나 **맥북(운영 서버)**으로 쾌적하게 이사할 시간입니다.
요청하신 대로 **"윈도우는 테스트용, 맥북은 운영용"**으로 완벽하게 분리하는 절차입니다.

---

## 1단계: Windows에서 준비하기 (현재 PC)

이미 제가 Docker 설정 파일(`Dockerfile`, `docker-compose.yml`)을 다 만들어뒀습니다.
사장님은 코드를 Git에 올리기만 하시면 됩니다.

1.  **Git 커밋 & 푸시**
    ```powershell
    git add .
    git commit -m "Prepare for Docker Migration"
    git push origin main
    ```

---

## 2단계: MacBook 세팅하기 (운영 서버)

이제 맥북을 켜세요. (터미널 앱 실행)

### 1. 필수 프로그램 설치
*   **Docker Desktop for Mac**: [설치 링크](https://www.docker.com/products/docker-desktop/) (설치 후 실행 필수)
*   **Git**: (터미널에 `git` 치면 설치하라고 뜸)

### 2. 코드 가져오기 (Clone)
```bash
# 원하는 폴더로 이동 (예: Documents)
cd Documents

# 코드 복사 (GitHub 주소는 사장님 레포지토리 주소로 변경하세요)
git clone [사장님_깃허브_주소_여기에] reason-hunter
cd reason-hunter
```

### 3. 데이터 및 설정 파일 이관 (★매우 중요★)
윈도우에 있는 **"데이터 파일"**은 Git에 올라가지 않으므로, **수동으로 복사**해서 맥북으로 옮겨야 합니다.
(카카오톡 나에게 보내기, USB, 구글 드라이브 등을 사용하세요)

#### 📂 가져와야 할 파일 목록
| 파일명 | 윈도우 위치 | 맥북에 넣을 위치 | 설명 |
| :--- | :--- | :--- | :--- |
| **subscribers.db** | 프로젝트 루트 폴더 | `reason-hunter/` (루트) | **핵심!** 구독자 정보 DB |
| **configs.py** | `common/` 폴더 | `reason-hunter/common/` | 설정 파일 |

*   **주의**: `subscribers.db`를 꼭 프로젝트 **최상위 폴더(reason-hunter 바로 안)**에 넣어주세요.

### 4. 환경 변수 설정 (`.env` 파일 생성)
맥북 `reason-hunter` 폴더 안에 `.env` 파일을 새로 만들고, **운영용 키**를 입력하세요.

```bash
# 맥북 터미널에서 .env 파일 생성
touch .env
open -e .env
```

**[.env 내용 예시 - 운영용]**
```ini
# 운영용(Real) 텔레그램 봇 토큰
TELEGRAM_BOT_TOKEN=123456:ABC-DEF-GHI... (운영용)

# 채널 ID (숫자)
TELEGRAM_VIP_CHANNEL_ID=-100xxxxxxx
TELEGRAM_FREE_CHANNEL_ID=-100yyyyyyy

# 한국투자증권 (KIS) - 실전투자 계좌 정보
KIS_APP_KEY=xxxx...
KIS_APP_SECRET=yyyy...
KIS_ACCOUNT_NO=xxxxx...

# 기타 설정
REDIS_HOST=redis
REDIS_PORT=6379
```

---

## 3단계: Docker로 서버 띄우기 (맥북)

이제 명령어 한 방이면 4개 서버(백엔드, 워커, 왓처, 프론트)가 동시에 켜집니다.
(Redis도 알아서 설치되고 실행됩니다!)

```bash
# 맥북 터미널 (reason-hunter 폴더)
docker-compose up -d --build
```

*   `up`: 실행해라
*   `-d`: 백그라운드에서 실행 (터미널 꺼도 꺼지지 않음)
*   `--build`: 최신 코드로 새로 조립해서 실행

**🎉 이관 완료!**
이제 `http://localhost:3000` 에 접속해보시면, 봇이 **맥북**에서 쌩쌩하게 돌아갈 겁니다.

---

## 4단계: 운영/개발 워크플로우 (사장님 요청사항)

이제 **"윈도우에서 수정 -> 맥북에 반영"** 하는 흐름입니다.

### 1️⃣ 윈도우 (테스트 서버)
*   윈도우 `.env`에는 **테스트용 봇 토큰**을 넣어두세요.
*   자유롭게 코드를 수정하고 테스트합니다.
*   수정이 끝나면 Git에 올립니다.
    ```powershell
    git add .
    git commit -m "새로운 기능 추가"
    git push
    ```

### 2️⃣ 맥북 (운영 서버) - 수정 금지 🚫
*   맥북에서는 코드를 절대 직접 고치지 마세요. **"받아오기"**만 합니다.
    ```bash
    # 1. 최신 코드 받기
    git pull

    # 2. 서버에 반영 (재시작)
    docker-compose up -d --build
    ```
    *   이 명령어를 치면 Docker가 변경된 부분만 알아서 다시 빌드하고 재시작합니다.

---

## 5단계: 문제 발생 시 (맥북)

*   **로그 확인**: `docker-compose logs -f worker` (봇 로그 실시간 보기)
*   **서버 끄기**: `docker-compose down`
*   **재부팅 후 실행**: `docker-compose up -d`
