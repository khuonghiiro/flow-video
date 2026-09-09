"""Test script — Wire Protocol API Verification.

Creates a project on Flow and tests T2V, R2V, F2F endpoints.
Run: .venv\\Scripts\\python.exe scripts/test_wire_protocol.py
"""
import json
import sys
import urllib.request
import time

BASE = "http://127.0.0.1:8100"
PROJECT_ID = "c5ece4c3-7db1-4230-b314-6a96f4348667"

def api(method, path, body=None, timeout=30):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        try:
            return e.code, json.loads(body_text)
        except Exception:
            return e.code, {"raw": body_text[:500]}
    except Exception as e:
        return 0, {"error": str(e)}


def test_health():
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)
    status, data = api("GET", "/health")
    ext = data.get("extension_connected", False)
    print(f"  Status: {status}")
    print(f"  Extension connected: {ext}")
    if not ext:
        print("  ⚠️  Extension NOT connected — video tests will fail")
        return False
    print("  ✅ Health OK")
    return True


def test_t2v():
    """Test Text-to-Video (YhhmEf) — 0 images, prompt only."""
    print("\n" + "=" * 60)
    print("TEST 2: T2V (Text-to-Video) → YhhmEf")
    print("=" * 60)
    body = {
        "prompt": "A golden sunset over calm ocean waves, cinematic 4K",
        "project_id": PROJECT_ID,
        "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
        "duration": "8",
        "model_family": "veo",
    }
    print(f"  Sending: POST /api/veo3/generate-video")
    print(f"  Prompt: {body['prompt'][:50]}...")
    print(f"  Expected RPC: YhhmEf, model: veo_3_1_t2v_lite_low_priority")

    status, data = api("POST", "/api/veo3/generate-video", body, timeout=120)
    print(f"  Response status: {status}")
    print(f"  Response: {json.dumps(data, ensure_ascii=False)[:500]}")

    if status == 200:
        ops = data.get("data", {}).get("operations", [])
        if ops:
            print(f"  ✅ T2V OK — operation: {ops[0].get('operation', {}).get('name', '?')[:20]}...")
            return True
        else:
            print(f"  ⚠️ T2V returned 200 but no operations")
    else:
        print(f"  ❌ T2V failed: {status}")
    return False


def test_t2v_4s():
    """Test T2V with 4s duration."""
    print("\n" + "=" * 60)
    print("TEST 3: T2V 4s → YhhmEf (veo_3_1_t2v_lite_4s_low_priority)")
    print("=" * 60)
    body = {
        "prompt": "A cat jumping over a fence in slow motion, cinematic",
        "project_id": PROJECT_ID,
        "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
        "duration": "4",
        "model_family": "veo",
    }
    print(f"  Sending: POST /api/veo3/generate-video (4s portrait)")
    status, data = api("POST", "/api/veo3/generate-video", body, timeout=120)
    print(f"  Response status: {status}")
    print(f"  Response: {json.dumps(data, ensure_ascii=False)[:500]}")

    if status == 200:
        print(f"  ✅ T2V 4s OK")
        return True
    print(f"  ❌ T2V 4s failed")
    return False


def test_r2v():
    """Test Reference-to-Video (MZZa6b) — needs actual reference media IDs."""
    print("\n" + "=" * 60)
    print("TEST 4: R2V (Reference-to-Video) → MZZa6b")
    print("=" * 60)
    print("  ⏭️  SKIPPED — requires uploaded reference images with valid media IDs")
    print("  (Would need: POST /api/veo3/generate-video-refs with reference_media_ids)")
    return None


def test_f2f():
    """Test Frame-to-Frame (nprQif) — needs actual start/end frame media IDs."""
    print("\n" + "=" * 60)
    print("TEST 5: F2F (Frame-to-Frame) → nprQif")
    print("=" * 60)
    print("  ⏭️  SKIPPED — requires start_image_media_id + end_image_media_id")
    print("  (Would need actual uploaded images on the Flow project)")
    return None


def test_model_resolvers():
    """Test that model resolvers return correct keys (no API call needed)."""
    print("\n" + "=" * 60)
    print("TEST 6: Model Resolver Verification (offline)")
    print("=" * 60)
    sys.path.insert(0, ".")
    from agent.flowkit_loader import bootstrap_flowkit
    bootstrap_flowkit()
    from agent.services import veo3_batch as vb

    tests = [
        ("T2V 4s", vb.resolve_t2v_model(4), "veo_3_1_t2v_lite_4s_low_priority"),
        ("T2V 6s", vb.resolve_t2v_model(6), "veo_3_1_t2v_lite_6s_low_priority"),
        ("T2V 8s", vb.resolve_t2v_model(8), "veo_3_1_t2v_lite_low_priority"),
        ("F2F 4s", vb.resolve_f2f_model(4), "veo_3_1_i2v_s_lite_4s_fl_low_priority"),
        ("F2F 6s", vb.resolve_f2f_model(6), "veo_3_1_i2v_s_lite_6s_fl_low_priority"),
        ("F2F 8s", vb.resolve_f2f_model(8), "veo_3_1_interpolation_lite_low_priority"),
        ("R2V default", vb.resolve_r2v_model(), "veo_3_1_r2v_lite_low_priority"),
        ("R2V ultra", vb.resolve_r2v_model("ultra"), "veo_3_1_r2v_fast_ultra"),
    ]

    all_pass = True
    for name, got, expected in tests:
        ok = got == expected
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}: {got}")
        if not ok:
            print(f"     Expected: {expected}")
            all_pass = False

    return all_pass


def test_builder_structure():
    """Test that builders produce correct item field counts."""
    print("\n" + "=" * 60)
    print("TEST 7: Builder Structure Verification (offline)")
    print("=" * 60)
    from agent.services import veo3_batch as vb

    # T2V: 5 fields
    t2v = vb.build_t2v_request("test", "proj", aspect="VIDEO_ASPECT_RATIO_LANDSCAPE", count=2)
    parsed = json.loads(json.loads(t2v)[0][0][1])
    t2v_count = len(parsed[0])
    t2v_fields = len(parsed[0][0])
    ok1 = t2v_count == 2 and t2v_fields == 5
    print(f"  {'✅' if ok1 else '❌'} T2V: count={t2v_count} (exp 2), fields={t2v_fields} (exp 5)")

    # R2V: 6 fields
    r2v = vb.build_r2v_request("test", "proj", ["ref1"], count=3)
    parsed2 = json.loads(json.loads(r2v)[0][0][1])
    r2v_count = len(parsed2[0])
    r2v_fields = len(parsed2[0][0])
    ok2 = r2v_count == 3 and r2v_fields == 6
    print(f"  {'✅' if ok2 else '❌'} R2V: count={r2v_count} (exp 3), fields={r2v_fields} (exp 6)")

    # F2F: 7 fields
    f2f = vb.build_f2f_request("test", "proj", "s1", "e1", count=4)
    parsed3 = json.loads(json.loads(f2f)[0][0][1])
    f2f_count = len(parsed3[0])
    f2f_fields = len(parsed3[0][0])
    ok3 = f2f_count == 4 and f2f_fields == 7
    print(f"  {'✅' if ok3 else '❌'} F2F: count={f2f_count} (exp 4), fields={f2f_fields} (exp 7)")

    return ok1 and ok2 and ok3


if __name__ == "__main__":
    results = {}
    
    results["health"] = test_health()
    if not results["health"]:
        print("\n⚠️  Extension not connected — skipping live API tests")
    else:
        results["t2v_8s"] = test_t2v()
        time.sleep(2)
        results["t2v_4s"] = test_t2v_4s()

    results["r2v"] = test_r2v()
    results["f2f"] = test_f2f()
    results["resolvers"] = test_model_resolvers()
    results["builders"] = test_builder_structure()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, result in results.items():
        if result is True:
            icon = "✅"
        elif result is False:
            icon = "❌"
        else:
            icon = "⏭️ "
        print(f"  {icon} {name}")
    
    failed = sum(1 for v in results.values() if v is False)
    if failed:
        print(f"\n❌ {failed} test(s) FAILED")
        sys.exit(1)
    else:
        print(f"\n✅ All tests passed!")
