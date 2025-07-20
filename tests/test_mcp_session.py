import requests
import time

GRAPHITI_URL = "http://localhost:8000/sse"  # Change this to your actual Graphiti /sse endpoint
RETRIES = 5
DELAY = 2  # seconds between retries

def get_session_id(graphiti_url):
    print(f"Requesting session from: {graphiti_url}")
    try:
        response = requests.get(graphiti_url, stream=True, timeout=10)
        if response.status_code == 200:
            # Try JSON
            try:
                data = response.json()
                session_id = data.get("session_id")
                if session_id:
                    print(f"[SUCCESS] Obtained session_id from JSON: {session_id}")
                    return session_id
            except Exception:
                pass
            # Try headers
            session_id = response.headers.get("session_id")
            if session_id:
                print(f"[SUCCESS] Obtained session_id from headers: {session_id}")
                return session_id
            # Try SSE stream
            for line in response.iter_lines():
                if b"session_id" in line:
                    session_id = line.decode().split(":")[-1].strip()
                    print(f"[SUCCESS] Obtained session_id from SSE: {session_id}")
                    return session_id
            print("[FAIL] Could not find session_id in response.")
        else:
            print(f"[FAIL] Status code: {response.status_code}, body: {response.text}")
    except Exception as e:
        print(f"[ERROR] Exception while requesting session: {e}")
    return None

if __name__ == "__main__":
    for i in range(RETRIES):
        print(f"\nAttempt {i+1} of {RETRIES}")
        session_id = get_session_id(GRAPHITI_URL)
        if session_id:
            print(f"[DONE] Successfully obtained session_id: {session_id}")
            break
        else:
            print(f"[RETRY] Waiting {DELAY} seconds before next attempt...")
            time.sleep(DELAY)
    else:
        print("[FAIL] Could not obtain a session_id after multiple attempts.") 