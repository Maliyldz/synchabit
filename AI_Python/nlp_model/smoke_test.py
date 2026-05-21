"""
SyncHabit NLP - Local Server Smoke Test
========================================
Bu script çalışan inference_server.py'ı HTTP üzerinden test eder.

Kullanım:
  1. Önce ayrı bir terminalde:  python inference_server.py
  2. Sonra bu terminalde:        python smoke_test.py
"""
import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8001"


def call(endpoint, method="GET", payload=None):
    url = f"{BASE_URL}{endpoint}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return None, str(e)


def test_health():
    print("\n" + "=" * 70)
    print("TEST 1: /health endpoint")
    print("=" * 70)
    status, body = call("/health")
    if status != 200:
        print(f"❌ HATA: status={status}, body={body}")
        print("   Server çalışıyor mu? Önce 'python inference_server.py' başlat.")
        return False
    print(f"✅ Status: {status}")
    print(f"   Model: {body.get('model')}")
    print(f"   Thresholds: BLOCK≥{body['thresholds']['block']}, WARN≥{body['thresholds']['warn']}")
    return True


def test_predict():
    print("\n" + "=" * 70)
    print("TEST 2: /predict endpoint — 3-tier + keyword + negation")
    print("=" * 70)

    cases = [
        # (text, expected_action, label)
        ("Bugün 5km koşacağım", "allow", "SAFE"),
        ("Python çalışacağım 2 saat", "allow", "SAFE"),
        ("Annemle alışverişe gideceğim", "allow", "SAFE"),
        ("Yarın annemin doğum günü hediye almam lazım", "allow", "SAFE"),
        ("Yeni proje için ekiple toplantı yapacağız", "allow", "SAFE"),

        ("Bileğimi keseceğim bu gece", "block", "HARD-BLOCK"),
        ("İntihar edeceğim", "block", "HARD-BLOCK"),
        ("Kendimi öldüreceğim", "block", "HARD-BLOCK"),
        ("Mavi balina görevini yapacağım", "block", "HARD-BLOCK"),
        ("Yüksek doz hap alacağım", "block", "HARD-BLOCK"),

        ("Bileğimi kesmeyeceğim artık", "allow", "NEGATION"),
        ("Kendimi öldürmeyeceğim asla", "allow", "NEGATION"),
        ("İntihar etmeyeceğim hayatı seviyorum", "allow", "NEGATION"),
        ("Eskiden kendime zarar veriyordum ama bıraktım", "allow", "RECOVERY"),

        ("Hap dolabını boşalttım hepsini birden içeceğim", "block", "ML-HIGH"),
        ("Çatıdan aşağı bakınca kendimi atmak istedim", "block", "ML-HIGH"),
    ]

    print(f"{'Label':<12} | {'Text':<54} | {'Got':<6} | {'Exp':<6} | Prob   | Result")
    print("-" * 110)

    passed = failed = 0
    for text, expected, label in cases:
        status, body = call("/predict", method="POST", payload={"text": text})
        if status != 200:
            print(f"❌ HTTP error: {status} {body}")
            failed += 1
            continue
        action = body["action"]
        prob = body["probability"]
        ok = action == expected
        short = text if len(text) <= 52 else text[:49] + "..."
        ind = "✅" if ok else "❌"
        print(f"{label:<12} | {short:<54} | {action:<6} | {expected:<6} | {prob:.3f} | {ind}")
        if ok:
            passed += 1
        else:
            failed += 1

    print("-" * 110)
    print(f"\nSonuç: {passed} geçti, {failed} kaldı")
    return failed == 0


def test_edge_cases():
    print("\n" + "=" * 70)
    print("TEST 3: Edge cases")
    print("=" * 70)

    # Empty
    s, b = call("/predict", method="POST", payload={"text": ""})
    print(f"Empty text         → status={s}, action={b.get('action') if s==200 else b}")
    # Missing field
    s, b = call("/predict", method="POST", payload={})
    print(f"Missing 'text'     → status={s} (expected 400)")
    # Non-string
    s, b = call("/predict", method="POST", payload={"text": 123})
    print(f"Numeric 'text'     → status={s} (expected 400)")
    # Wrong endpoint
    s, b = call("/foo", method="GET")
    print(f"Wrong endpoint     → status={s} (expected 404)")


def main():
    print("SyncHabit NLP Server — Smoke Test")
    print(f"Target: {BASE_URL}")

    if not test_health():
        sys.exit(1)
    ok = test_predict()
    test_edge_cases()
    print("\n" + ("✅ TÜM TESTLER GEÇTİ" if ok else "⚠️ BAZI TESTLER KALDI"))


if __name__ == "__main__":
    main()