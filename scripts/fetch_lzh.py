import argparse
import csv
import hashlib
import os
import time
from datetime import datetime, timedelta
import requests

BASE_B = "http://www1.mbrace.or.jp/od2/B/{yyyymm}/b{yymmdd}.lzh"
BASE_K = "http://www1.mbrace.or.jp/od2/K/{yyyymm}/k{yymmdd}.lzh"

def daterange(start: str, end: str):
    s = datetime.strptime(start, "%Y%m%d")
    e = datetime.strptime(end, "%Y%m%d")
    cur = s
    while cur <= e:
        yield cur
        cur += timedelta(days=1)

def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def fetch(url: str, timeout=30):
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "boatrace-data-lake/1.0"})
    return r

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default="raw")
    ap.add_argument("--sleep", type=float, default=1.2)
    args = ap.parse_args()

    out = args.out
    logdir = os.path.join(out, "meta")
    ensure_dir(logdir)
    logpath = os.path.join(logdir, "ingest_log.csv")
    newfile = not os.path.exists(logpath)

    with open(logpath, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if newfile:
            w.writerow(["ts_utc", "kind", "date", "url", "status", "bytes", "sha256"])

        for d in daterange(args.start, args.end):
            yyyymm = d.strftime("%Y%m")
            yymmdd = d.strftime("%y%m%d")
            yyyymmdd = d.strftime("%Y%m%d")

            targets = [
                ("B", BASE_B.format(yyyymm=yyyymm, yymmdd=yymmdd)),
                ("K", BASE_K.format(yyyymm=yyyymm, yymmdd=yymmdd)),
            ]

            for kind, url in targets:
                try:
                    r = fetch(url)
                    status = r.status_code
                    if status == 200 and r.content:
                        folder = os.path.join(out, "lzh", kind, yyyymm)
                        ensure_dir(folder)
                        fname = ("b" if kind == "B" else "k") + yymmdd + ".lzh"
                        path = os.path.join(folder, fname)
                        with open(path, "wb") as wf:
                            wf.write(r.content)
                        w.writerow([datetime.utcnow().isoformat(), kind, yyyymmdd, url, status, len(r.content), sha256_bytes(r.content)])
                    else:
                        # 404 etc are normal (no races)
                        w.writerow([datetime.utcnow().isoformat(), kind, yyyymmdd, url, status, 0, ""])
                except Exception as e:
                    w.writerow([datetime.utcnow().isoformat(), kind, yyyymmdd, url, "EXC:" + str(e), 0, ""])
                time.sleep(args.sleep)

if __name__ == "__main__":
    main()
