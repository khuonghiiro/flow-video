import json, urllib.request, sys
sys.stdout.reconfigure(encoding='utf-8')

req = urllib.request.Request(
    "http://127.0.0.1:8100/api/flow/check-status",
    data=json.dumps({
        "operations": [
            {
                "name": "a6accfab-618d-4ff1-b229-0395f853b6fb",
                "projectId": "4c6ba350-a18d-4b05-ae59-67f076ba1883"
            },
            {
                "name": "a6accfab-618d-4ff1-b229-0395f853b6fb_upsampled",
                "projectId": "4c6ba350-a18d-4b05-ae59-67f076ba1883"
            }
        ]
    }).encode("utf-8"),
    headers={"Content-Type": "application/json", "Accept": "application/json"}
)
try:
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read())
        print("Response:", json.dumps(data, indent=2))
except Exception as e:
    print("Error:", e)
    if hasattr(e, "read"):
        print("Error body:", e.read().decode("utf-8"))
