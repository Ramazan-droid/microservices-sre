import requests
import threading
import time
import sys
import random

BASE_URL = "http://34.134.188.139:8002"

RESULTS = {
    "success": 0,
    "error": 0,
    "total_time": 0,
}

RESPONSE_TIMES = []
LOCK = threading.Lock()


def hit_endpoint():
    start = time.time()
    try:
        # Randomly choose endpoint (simulate real usage)
        if random.random() < 0.7:
            # 70% GET requests
            url = f"{BASE_URL}/api/orders"
            r = requests.get(url, timeout=5)
        else:
            # 30% POST requests
            url = f"{BASE_URL}/api/orders"
            payload = {
                "item": "test-item",
                "quantity": random.randint(1, 5)
            }
            r = requests.post(url, json=payload, timeout=5)

        elapsed = time.time() - start

        with LOCK:
            RESULTS["total_time"] += elapsed
            RESPONSE_TIMES.append(elapsed)

            if r.status_code == 200 or r.status_code == 201:
                RESULTS["success"] += 1
            else:
                RESULTS["error"] += 1

    except Exception:
        with LOCK:
            RESULTS["error"] += 1


def percentile(data, p):
    if not data:
        return 0
    k = int(len(data) * p)
    return data[min(k, len(data) - 1)]


def run_load_test(concurrent_users=20, duration_seconds=60):
    print(f"Starting load test: {concurrent_users} users for {duration_seconds}s")

    end_time = time.time() + duration_seconds
    threads = []

    while time.time() < end_time:
        # Maintain number of concurrent threads
        threads = [t for t in threads if t.is_alive()]

        while len(threads) < concurrent_users:
            t = threading.Thread(target=hit_endpoint)
            t.start()
            threads.append(t)

        # Small sleep to avoid CPU overuse but still high pressure
        time.sleep(0.01)

    # Wait for all threads to finish
    for t in threads:
        t.join()

    total = RESULTS["success"] + RESULTS["error"]
    avg_time = RESULTS["total_time"] / total if total > 0 else 0

    RESPONSE_TIMES.sort()

    print("\n=== Load Test Results ===")
    print(f"Total requests: {total}")
    print(f"Success: {RESULTS['success']}")
    print(f"Errors:  {RESULTS['error']}")
    print(f"Avg response time: {avg_time:.3f}s")

    print("\n--- Latency Percentiles ---")
    print(f"P50: {percentile(RESPONSE_TIMES, 0.5):.3f}s")
    print(f"P95: {percentile(RESPONSE_TIMES, 0.95):.3f}s")
    print(f"P99: {percentile(RESPONSE_TIMES, 0.99):.3f}s")


if __name__ == "__main__":
    users = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60

    run_load_test(users, duration)