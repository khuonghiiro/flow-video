import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

req = urllib.request.Request(
    "http://127.0.0.1:8100/api/projects/4c6ba350-a18d-4b05-ae59-67f076ba1883",
    headers={"accept": "application/json"}
)
try:
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read())
        print("Local project detail:", data)
except Exception as e:
    print("Local project detail error:", e)
