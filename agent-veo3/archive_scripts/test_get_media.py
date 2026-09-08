import urllib.request, urllib.error, json, sys
sys.stdout.reconfigure(encoding='utf-8')

def test_media(media_id, project_id=""):
    url = f"http://127.0.0.1:8100/api/flow/media/{media_id}"
    if project_id:
        url += f"?project_id={project_id}"
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read())
            print("Response:", data)
    except urllib.error.HTTPError as e:
        print("HTTPError:", e.code, e.reason, e.read().decode('utf-8', errors='replace'))
    except Exception as e:
        print("Error:", e)

test_media("e8a30373-3e9f-4381-a452-ac8b48374cb8", "2383473a-b49c-4ba3-9814-07cd2c547743")
