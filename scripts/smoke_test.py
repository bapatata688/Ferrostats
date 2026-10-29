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

    if all_ok:
        print("\n>>> ALL HTTP AND UI VERIFICATIONS PASSED SUCCESSFULLY! <<<")
    return all_ok

if __name__ == '__main__':
    base = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
    success = run_smoke_test(base)
    if not success:
        sys.exit(1)
