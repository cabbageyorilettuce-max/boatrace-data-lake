import argparse
import os
from datetime import datetime, timedelta
import pandas as pd

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def daterange(start: str, end: str):
    s = datetime.strptime(start, "%Y%m%d")
    e = datetime.strptime(end, "%Y%m%d")
    cur = s
    while cur <= e:
        yield cur.strftime("%Y%m%d")
        cur += timedelta(days=1)

def count_files(root: str, prefix: str):
    p = os.path.join(root, prefix)
    if not os.path.exists(p):
        return 0
    cnt = 0
    for _, _, files in os.walk(p):
        cnt += len([f for f in files if f.endswith(".html") or f.endswith(".lzh")])
    return cnt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hd", required=False)
    ap.add_argument("--start", required=False)
    ap.add_argument("--end", required=False)
    ap.add_argument("--raw", default="raw")
    ap.add_argument("--curated", default="curated")
    args = ap.parse_args()

    if args.hd:
        hds = [args.hd]
    else:
        if not (args.start and args.end):
            raise SystemExit("need --hd or (--start and --end)")
        hds = list(daterange(args.start, args.end))

    ensure_dir(args.curated)

    rows = []
    for hd in hds:
        rows.append({
            "hd": hd,
            "raw_lzh_B_files": count_files(args.raw, os.path.join("lzh", "B")),
            "raw_lzh_K_files": count_files(args.raw, os.path.join("lzh", "K")),
            "raw_html_beforeinfo_files": count_files(args.raw, os.path.join("html", "beforeinfo", f"hd={hd}")),
            "raw_html_odds3t_files": count_files(args.raw, os.path.join("html", "odds3t", f"hd={hd}")),
            "raw_html_odds2tf_files": count_files(args.raw, os.path.join("html", "odds2tf", f"hd={hd}")),
            "updated_utc": datetime.utcnow().isoformat(),
        })

    out_csv = os.path.join(args.curated, "ingest_days.csv")
    df_new = pd.DataFrame(rows)

    if os.path.exists(out_csv):
        df_old = pd.read_csv(out_csv, dtype=str)
        # hdで上書き
        df = pd.concat([df_old, df_new]).drop_duplicates(subset=["hd"], keep="last")
    else:
        df = df_new

    df = df.sort_values("hd")
    df.to_csv(out_csv, index=False)

if __name__ == "__main__":
    main()
