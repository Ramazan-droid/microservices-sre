import requests
import threading
import time
import sys

BASE_URL = "http://localhost"
RESULTS = {"success": 0, "error": 0, "total_time": 0}
LOCK = threading.Lock()

def hit_endpoint(url):
    start = time.time()
    try:
        r = requests.get(url, timeout=5)
        elapsed = time.time() - start
        with LOCK:
            RESULTS["total_time"] += elapsed
            if r.status_code == 200:
                RESULTS["success"] += 1
            else:
                RESULTS["error"] += 1
    except Exception:
        with LOCK:
            RESULTS["error"] += 1

def run_load_test(concurrent_users=20, duration_seconds=60):
    print(f"Starting load test: {concurrent_users} users for {duration_seconds}s")
    endpoints = [
        f"{BASE_URL}/api/auth/health",
        f"{BASE_URL}/api/products/health",
        f"{BASE_URL}/api/orders/health",
    ]
    end_time = time.time() + duration_seconds
    threads = []
    while time.time() < end_time:
        for url in endpoints:
            if len(threads) < concurrent_users:
                t = threading.Thread(target=hit_endpoint, args=(url,))
                t.start()
                threads.append(t)
        threads = [t for t in threads if t.is_alive()]
        time.sleep(0.1)

    for t in threads:
        t.join()

    total = RESULTS["success"] + RESULTS["error"]
    avg_time = RESULTS["total_time"] / total if total > 0 else 0
    print(f"\n=== Load Test Results ===")
    print(f"Total requests: {total}")
    print(f"Success: {RESULTS['success']}")
    print(f"Errors:  {RESULTS['error']}")
    print(f"Avg response time: {avg_time:.3f}s")

if __name__ == "__main__":
    users = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    run_load_test(users, duration)