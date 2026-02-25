import argparse
import os
import time
from datetime import datetime
import requests
from lxml import html

INDEX = "https://www.boatrace.jp/owpc/pc/race/index?hd={hd}"
BEFOREINFO = "https://www.boatrace.jp/owpc/pc/race/beforeinfo?hd={hd}&jcd={jcd}&rno={rno}"
ODDS3T = "https://www.boatrace.jp/owpc/pc/race/odds3t?hd={hd}&jcd={jcd}&rno={rno}"
ODDS2TF = "https://www.boatrace.jp/owpc/pc/race/odds2tf?hd={hd}&jcd={jcd}&rno={rno}"

HEADERS = {"User-Agent": "boatrace-data-lake/1.0"}

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def get_jcds(hd: str):
    r = requests.get(INDEX.format(hd=hd), headers=HEADERS, timeout=30)
    r.raise_for_status()
    doc = html.fromstring(r.text)

    # ページ内に jcd=XX が複数出るので、リンクから抽出
    links = doc.xpath("//a/@href")
    jcds = set()
    for u in links:
        if "jcd=" in u:
            # crude parse
            try:
                part = u.split("jcd=")[1]
                jcd = part.split("&")[0].split("#")[0]
                if len(jcd) == 2 and jcd.isdigit():
                    jcds.add(jcd)
            except Exception:
                pass
    return sorted(jcds)

def save_html(out_root: str, typ: str, hd: str, jcd: str, rno: int, body: str):
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    folder = os.path.join(out_root, "html", typ, f"hd={hd}", f"jcd={jcd}", f"rno={rno:02d}")
    ensure_dir(folder)
    path = os.path.join(folder, f"ts={ts}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)

def fetch(url: str):
    r = requests.get(url, headers=HEADERS, timeout=30)
    return r.status_code, r.text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hd", required=True)
    ap.add_argument("--out", default="raw")
    ap.add_argument("--sleep", type=float, default=0.8)
    args = ap.parse_args()

    jcds = get_jcds(args.hd)
    if not jcds:
        print(f"[WARN] no jcd found for hd={args.hd} (no races or page structure changed)")
        return

    for jcd in jcds:
        for rno in range(1, 13):
            for typ, tpl in [
                ("beforeinfo", BEFOREINFO),
                ("odds3t", ODDS3T),
                ("odds2tf", ODDS2TF),
            ]:
                url = tpl.format(hd=args.hd, jcd=jcd, rno=rno)
                try:
                    status, text = fetch(url)
                    if status == 200 and text and "boatrace" in text.lower():
                        save_html(args.out, typ, args.hd, jcd, rno, text)
                    else:
                        # 存在しないR/非開催などもあるので無視
                        pass
                except Exception as e:
                    print(f"[WARN] {typ} hd={args.hd} jcd={jcd} rno={rno}: {e}")
                time.sleep(args.sleep)

if __name__ == "__main__":
    main()
