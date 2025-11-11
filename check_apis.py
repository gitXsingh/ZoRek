import json
import time
from datetime import datetime

import requests

# Import API keys/URLs from the app without starting the server
from app import OMDB_KEY, SPOONACULAR_KEY, SHEET_BEST_URL


def check(label, fn):
    start = time.time()
    try:
        ok, details = fn()
        status = "PASS" if ok else "FAIL"
        elapsed_ms = int((time.time() - start) * 1000)
        print(f"[{status}] {label} ({elapsed_ms} ms) - {details}")
        return ok
    except Exception as exc:
        elapsed_ms = int((time.time() - start) * 1000)
        print(f"[FAIL] {label} ({elapsed_ms} ms) - Exception: {exc}")
        return False


def test_omdb():
    url = f"https://www.omdbapi.com/?apikey={OMDB_KEY}&s=action"
    r = requests.get(url, timeout=15)
    data = r.json()
    ok = (r.status_code == 200) and (data.get("Response") == "True") and bool(data.get("Search"))
    details = f"status={r.status_code}, results={len(data.get('Search', []))}"
    return ok, details


def test_google_books():
    url = "https://www.googleapis.com/books/v1/volumes?q=subject:action"
    r = requests.get(url, timeout=15)
    data = r.json()
    ok = (r.status_code == 200) and ("items" in data) and len(data["items"]) > 0
    details = f"status={r.status_code}, items={len(data.get('items', []))}"
    return ok, details


def test_spoonacular():
    url = f"https://api.spoonacular.com/recipes/random?apiKey={SPOONACULAR_KEY}&number=1"
    r = requests.get(url, timeout=20)
    data = r.json()
    ok = (r.status_code == 200) and ("recipes" in data) and len(data["recipes"]) > 0
    details = f"status={r.status_code}, recipes={len(data.get('recipes', []))}"
    return ok, details


def test_sheetbest():
    payload = {
        "Name": "HealthCheck",
        "Email": "healthcheck@example.com",
        "Choice": "Health",
        "Genre": "n/a",
        "Mood": "n/a",
        "Suggestion": "n/a",
        "Timestamp": datetime.utcnow().isoformat()
    }
    r = requests.post(SHEET_BEST_URL, json=payload, timeout=15)
    ok = r.status_code in (200, 201)
    details = f"status={r.status_code}, body_prefix={json.dumps(r.json())[:80] if r.headers.get('content-type','').startswith('application/json') else r.text[:80]}"
    return ok, details


def test_local_endpoint(choice, genre):
    url = "http://127.0.0.1:5000/zorek"
    r = requests.post(url, json={"choice": choice, "genre": genre}, timeout=10)
    ok = (r.status_code == 200) and ("suggestion" in r.json())
    details = f"status={r.status_code}, resp={r.text[:80]}"
    return ok, details


if __name__ == "__main__":
    print("=== External API Checks ===")
    passed = 0
    total = 0

    for label, fn in [
        ("OMDb search", test_omdb),
        ("Google Books subject search", test_google_books),
        ("Spoonacular random recipe", test_spoonacular),
        ("Sheet.best logging POST", test_sheetbest),
    ]:
        total += 1
        if check(label, fn):
            passed += 1

    print("\n=== Local Endpoint Checks (requires server running on :5000) ===")
    for label, fn in [
        ("Local /zorek Movies", lambda: test_local_endpoint("Movies", "action")),
        ("Local /zorek Books", lambda: test_local_endpoint("Books", "fiction")),
        ("Local /zorek Food", lambda: test_local_endpoint("Food", "pizza")),
    ]:
        total += 1
        if check(label, fn):
            passed += 1

    print(f"\nSummary: {passed}/{total} checks passed")

