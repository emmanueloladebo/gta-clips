import json
import urllib.request
import urllib.parse

def test():
    # 1. Login
    data = urllib.parse.urlencode({"username": "admin", "password": "GTA6ClipsPass!2026"}).encode()
    req = urllib.request.Request("http://localhost/api/auth/login", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req) as resp:
        token = json.loads(resp.read().decode())["access_token"]
    print("Auth OK, token obtained.")

    # 2. Trigger instant capture
    req2 = urllib.request.Request("http://localhost/api/streamers/1/capture-now?duration=15", method="POST", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req2) as resp2:
        print(f"Status Code: {resp2.status}")
        print(f"Response Body: {resp2.read().decode()}")

if __name__ == "__main__":
    test()
