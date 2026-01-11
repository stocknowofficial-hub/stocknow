import requests
import json
import os

BACKEND_URL = "http://127.0.0.1:8000"
BACKUP_FILE = "backup_subscribers.json"

def backup():
    print("📥 Backing up subscribers...")
    try:
        res = requests.get(f"{BACKEND_URL}/subscribers/detail")
        data = res.json()
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Backup saved to {BACKUP_FILE} ({len(data)} users)")
        print(data)
    except Exception as e:
        print(f"❌ Backup failed: {e}")

def restore():
    print("📤 Restoring subscribers...")
    if not os.path.exists(BACKUP_FILE):
        print("❌ Backup file not found!")
        return

    with open(BACKUP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for user in data:
        # 새로운 스키마에 맞춰 복구 (기본값 설정)
        payload = {
            "chat_id": user["chat_id"],
            "name": user["name"],
            # 새 필드들 (기본값)
            "username": f"unknown_{user['chat_id']}", # 임시
            "tier": "FREE",
            "expiry_date": None
        }
        
        # 1. 생성 (POST)
        try:
            # POST endpoint가 변경될 것이므로, 여기서는 새로 만든 'restore'용 로직을 짜야 함.
            # 하지만 기존 POST /subscribers 는 'chat_id'와 'name'만 받고 나머지는 default로 생성함.
            # 따라서 그냥 POST 호출하고, 추가 정보(active status 등)는 PUT으로 업데이트해야 할 수도 있음.
            # 일단 POST로 기본 생성
            res = requests.post(f"{BACKEND_URL}/subscribers", json={"chat_id": user["chat_id"], "name": user["name"], "username": payload["username"]})
            print(f"Restore {user['name']}: {res.status_code}")
            
            # 2. 상태 복구 (Active 여부)
            if not user["is_active"]:
                requests.put(f"{BACKEND_URL}/subscribers/{user['chat_id']}", json={"is_active": False})
                print(f"Set Inactive {user['name']}")
                
        except Exception as e:
            print(f"Failed to restore {user['chat_id']}: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        restore()
    else:
        backup()
