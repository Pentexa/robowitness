"""Exercise live AI routes against the running backend (sanitized output only)."""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:120]}


import urllib.error

print("== POST /api/scenarios/generate ==", flush=True)
st, body = post("/api/scenarios/generate", {"objective": "crowded crossing"})
if st == 200:
    spec = body["scenario"]
    print("status=200 provenance=%s id=%s kind=%s obstacles=%d" % (
        body["provenance"], spec["id"], spec["kind"], len(spec["obstacles"])), flush=True)
else:
    print("status=%s body=%s" % (st, body), flush=True)

print("== POST /api/failures/<run>/investigate ==", flush=True)
st2, body2 = post("/api/failures/run-904791dba73e/investigate", {})
if st2 == 200:
    print("status=200 provenance=%s tick=%s patch_keys=%s" % (
        body2["provenance"], body2["failure_tick"],
        sorted((body2.get("suggested_patch") or {}).keys())), flush=True)
else:
    print("status=%s body=%s" % (st2, body2), flush=True)
