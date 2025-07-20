import requests

BASE_URL = "http://localhost:8000"  # Change if needed

# 1. GET /sse with SSE headers
def try_get_sse_with_headers():
    print("\n[1] GET /sse with Accept: text/event-stream")
    url = f"{BASE_URL}/sse"
    headers = {"Accept": "text/event-stream"}
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        print("Status:", response.status_code)
        print("Headers:", response.headers)
        for line in response.iter_lines():
            print("Line:", line)
            if b"session_id" in line:
                print("Found session_id in SSE:", line)
                break
    except Exception as e:
        print("[ERROR]", e)

# 2. POST /session with JSON-RPC
def try_post_session_jsonrpc():
    print("\n[2] POST /session with JSON-RPC")
    url = f"{BASE_URL}/session"
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "session/create",
        "params": {}
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print("Status:", response.status_code)
        print("Headers:", response.headers)
        print("Body:", response.text)
    except Exception as e:
        print("[ERROR]", e)

# 3. GET /session
def try_get_session():
    print("\n[3] GET /session")
    url = f"{BASE_URL}/session"
    try:
        response = requests.get(url, timeout=10)
        print("Status:", response.status_code)
        print("Headers:", response.headers)
        print("Body:", response.text)
    except Exception as e:
        print("[ERROR]", e)

# 4. POST /sse with JSON-RPC
def try_post_sse_jsonrpc():
    print("\n[4] POST /sse with JSON-RPC")
    url = f"{BASE_URL}/sse"
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "session/create",
        "params": {}
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print("Status:", response.status_code)
        print("Headers:", response.headers)
        print("Body:", response.text)
    except Exception as e:
        print("[ERROR]", e)

# 5. GET /sse with no special headers
def try_get_sse_plain():
    print("\n[5] GET /sse (plain)")
    url = f"{BASE_URL}/sse"
    try:
        response = requests.get(url, timeout=10)
        print("Status:", response.status_code)
        print("Headers:", response.headers)
        print("Body:", response.text)
    except Exception as e:
        print("[ERROR]", e)

if __name__ == "__main__":
    try_get_sse_with_headers()
    try_post_session_jsonrpc()
    try_get_session()
    try_post_sse_jsonrpc()
    try_get_sse_plain() 