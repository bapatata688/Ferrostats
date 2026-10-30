import urllib.request
import json
import sys

def run_smoke_test(base_url: str = 'http://127.0.0.1:8080') -> bool:
    checks = [
        ('/', 200, 'text/html'),
        ('/pos', 200, 'text/html'),
        ('/static/pos.js', 200, 'text/javascript'),
        ('/static/img/logo.jpg', 200, 'image/jpeg'),
        ('/static/styles.css', 200, 'text/css'),
        ('/static/app.js', 200, 'text/javascript'),
        ('/health', 200, 'application/json'),
        ('/api/v1/analytics/dashboard', 200, 'application/json'),
        ('/api/v1/products', 200, 'application/json'),
    ]

    all_ok = True
    for path, expected_status, content_type_part in checks:
        try:
            req = urllib.request.Request(base_url + path, headers={'X-User-Role': 'ADMIN', 'X-User-Id': '1'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
                ct = resp.headers.get('Content-Type', '')
                data = resp.read()
                if status != expected_status:
                    print(f"FAIL {path}: status {status} != {expected_status}")
                    all_ok = False
                else:
                    print(f"OK   {path:<25} -> HTTP {status} ({len(data)} bytes, {ct})")
        except Exception as e:
            print(f"ERR  {path}: {e}")
            all_ok = False

    # Idempotency replay verification on POS checkout
    try:
        import time
        test_uuid = f"smoke-test-uuid-{int(time.time())}"
        payload = json.dumps({
            "transaction_uuid": test_uuid,
            "user_id": 3,
            "customer_type": "CONSUMIDOR_FINAL",
            "payment_method": "EFECTIVO",
            "items": [{"product_id": 1, "quantity": 1}]
        }).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-User-Role": "CASHIER",
            "X-User-Id": "3"
        }

        # 1. First checkout
        req1 = urllib.request.Request(base_url + "/api/v1/pos/checkout", data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req1, timeout=5) as resp1:
            data1 = json.loads(resp1.read().decode())
            sale_id_1 = data1.get("sale_id")
            if resp1.status == 201 and sale_id_1:
                print(f"OK   POS Checkout (Create)     -> HTTP 201 (Sale #{sale_id_1})")
            else:
                print(f"FAIL POS Checkout (Create): status {resp1.status}")
                all_ok = False

        # 2. Idempotent replay with identical transaction_uuid
        req2 = urllib.request.Request(base_url + "/api/v1/pos/checkout", data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req2, timeout=5) as resp2:
            data2 = json.loads(resp2.read().decode())
            sale_id_2 = data2.get("sale_id")
            is_replay = resp2.headers.get("Idempotent-Replay") == "true"
            if resp2.status == 200 and sale_id_2 == sale_id_1 and is_replay:
                print(f"OK   POS Checkout (Replay)     -> HTTP 200 (Idempotent-Replay: true, Sale #{sale_id_2})")
            else:
                print(f"FAIL POS Checkout (Replay): status {resp2.status}, is_replay={is_replay}, sale_id={sale_id_2}")
                all_ok = False
    except Exception as e:
        print(f"ERR  POS Checkout Idempotency: {e}")
        all_ok = False

    if all_ok:
        print("\n>>> ALL HTTP AND UI VERIFICATIONS PASSED SUCCESSFULLY! <<<")
    return all_ok

if __name__ == '__main__':
    base = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
    success = run_smoke_test(base)
    if not success:
        sys.exit(1)
