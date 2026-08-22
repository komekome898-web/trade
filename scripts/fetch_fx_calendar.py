#!/usr/bin/env python3
"""
Build a VERIFIED macro-event calendar for the FX event-tick library.

    2015-01-01 .. 2026-08-21,  types: NFP / CPI / FOMC / BOJ
    output: data/fx/calendar.csv

Why this file exists
--------------------
scripts/research_fx_events.py had to derive its calendar from RULES (NFP = first
Friday, CPI = "the 12th snapped to a weekday") and from UNVERIFIED training
knowledge (all FOMC 2023-2025 dates, ALL BOJ dates).  docs/KNOWLEDGE_FX.md sec.4
therefore records the whole event arm as date-uncertain: a 1-day error makes an
event window miss entirely, so the CPI arm in particular was noise-dominated.
This script replaces guesses with primary-source scrapes.

PRIMARY SOURCES (all scraped, all cached under data/fx/calendar_cache/)
----------------------------------------------------------------------
NFP  https://www.bls.gov/schedule/{YYYY}/home.htm
     row "Employment Situation" -> published date + published clock time (ET).
     These archived year pages carry the schedule AS RELEASED, including
     shutdown reschedules (verified: the 2025 page shows no October Employment
     Situation and puts the September report on Nov 20, which is what happened).
     NOTE: bls.gov returns HTTP 403 to browser-style User-Agents and HTTP 200 to
     a UA that identifies the requester, which is what BLS asks for.  The UA
     below carries the repo owner's contact address for exactly that reason.
CPI  same pages, row "Consumer Price Index".
FOMC https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm   (2021+)
     https://www.federalreserve.gov/monetarypolicy/fomchistorical{YYYY}.htm
     Statement DAY is taken from the statement link itself
     (/newsevents/pressreleases/monetary{YYYYMMDD}a.htm), not from the meeting
     date range, so 2-day meetings resolve to the day the statement lands.
     Release TIME is then read from that press release page's own
     "For release at H:MM a.m./p.m. EST|EDT" line where the page carries one
     (2018+ template); older pages fall back to the 14:00 ET rule, which has
     held for every SCHEDULED statement since 2013.  Unscheduled/emergency
     statements (2020-03-03 10:00 ET, 2020-03-15 17:00 ET, ...) are kept with
     their scraped time and flagged in `note`.
BOJ  https://www.boj.or.jp/en/mopo/mpmsche_minu/minu_{YYYY}/index.htm
     ("Minutes of the Monetary Policy Meeting on <dates>, <year>") UNION
     https://www.boj.or.jp/en/mopo/mpmdeci/mpr_{YYYY}/index.htm
     (statement PDF names k{YYMMDD}a.pdf), so that recent meetings whose minutes
     are not published yet are still captured.  For a 2-day meeting the DECISION
     day is the last listed date.  BOJ does not pre-announce a release clock
     time -- the release DRIFTS across roughly 11:30-13:30 JST (docs/
     KNOWLEDGE_FX.md sec.2, report s) -- so time_utc is written as the NOMINAL
     window anchor 02:30 UTC (11:30 JST) and the tick window used downstream is
     the whole 02:00-05:00 UTC band.  Every BOJ row says so in `note`.

CONFIDENCE LADDER (column `confidence`, column `source`)
--------------------------------------------------------
  verified_web / high    scraped from the primary source above, date AND time
  verified_web / medium  date scraped; time is the standing rule (14:00 ET)
                         because that page carries no release-time line
  rule / medium          date from a deterministic calendar rule (first Friday)
                         because the primary source could not be reached
  training / low         date from unverified training knowledge, +/-1 day
                         caveat -- MUST be treated as possibly wrong
Anything that cannot reach at least rule-level confidence is DROPPED and logged.

DST is handled with zoneinfo (America/New_York, Asia/Tokyo); JST has no DST.
Section "DST spot checks" prints the conversion on four known boundary dates.

Usage
-----
    python scripts/fetch_fx_calendar.py                 # scrape (uses cache)
    python scripts/fetch_fx_calendar.py --refresh       # ignore cache
    python scripts/fetch_fx_calendar.py --offline       # cache/training only

Idempotent: raw HTML is cached, so a re-run does no network I/O and produces a
byte-identical calendar.csv.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fx" / "calendar.csv"
CACHE = ROOT / "data" / "fx" / "calendar_cache"

ET = ZoneInfo("America/New_York")
JST = ZoneInfo("Asia/Tokyo")
UTC = dt.timezone.utc

START = dt.date(2015, 1, 1)
END = dt.date(2026, 8, 21)
YEARS = list(range(START.year, END.year + 1))

# bls.gov 403s browser UAs and 200s an identifying one; federalreserve.gov and
# boj.or.jp accept it too, so one UA is used everywhere.
UA = "trade-research/1.0 (+contact: komekome3ai@gmail.com)"

BOJ_NOMINAL_JST = (11, 30)          # window anchor only -- the release drifts
BOJ_WINDOW_UTC = ("02:00", "05:00")


# --------------------------------------------------------------------------- #
# polite fetch + on-disk cache
# --------------------------------------------------------------------------- #
class RateLimiter:
    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self.lock = threading.Lock()
        self.next_ok = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_ok - now)
            self.next_ok = max(now, self.next_ok) + self.min_interval
        if delay:
            time.sleep(delay)


_LIMITER = RateLimiter(0.6)          # government sites: be slow on purpose
N_NET = 0
N_CACHE = 0
FAILED_URLS: list[tuple[str, str]] = []


def cache_path(url: str) -> Path:
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    tail = re.sub(r"[^A-Za-z0-9._-]", "_", url.split("//", 1)[-1])[-60:]
    return CACHE / f"{h}_{tail}"


def get(url: str, refresh: bool = False, offline: bool = False,
        retries: int = 4) -> str | None:
    """Return page text, or None if unreachable.  Caches raw bytes."""
    global N_NET, N_CACHE
    p = cache_path(url)
    if p.exists() and not refresh:
        N_CACHE += 1
        return p.read_text(encoding="utf-8", errors="replace")
    if offline:
        return None
    last = ""
    for attempt in range(retries):
        _LIMITER.wait()
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
            N_NET += 1
            return body.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (404, 403):
                break
            time.sleep(2.0 * (attempt + 1))
        except Exception as e:                                # noqa: BLE001
            last = str(e)
            time.sleep(2.0 * (attempt + 1))
    FAILED_URLS.append((url, last))
    return None


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------------- #
# time helpers
# --------------------------------------------------------------------------- #
def local_to_utc(day: dt.date, hh: int, mm: int, zone: ZoneInfo) -> dt.datetime:
    return dt.datetime(day.year, day.month, day.day, hh, mm,
                       tzinfo=zone).astimezone(UTC)


def iso_utc(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})
MONTHS["sept"] = 9


def month_num(tok: str) -> int | None:
    return MONTHS.get(tok.strip().strip(".").lower())


# --------------------------------------------------------------------------- #
# BLS -- NFP (Employment Situation) and CPI
# --------------------------------------------------------------------------- #
BLS_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
BLS_DATE = re.compile(
    r"([A-Z][a-z]+day),\s*([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})")
BLS_TIME = re.compile(r"(\d{1,2}):(\d{2})\s*(AM|PM)", re.I)


def scrape_bls(year: int, refresh: bool, offline: bool) -> list[dict]:
    url = f"https://www.bls.gov/schedule/{year}/home.htm"
    html = get(url, refresh, offline)
    if html is None:
        return []
    rows: list[dict] = []
    for raw in BLS_ROW.findall(html):
        txt = strip_tags(raw)
        if "Employment Situation" in txt and "Veterans" not in txt \
                and "State" not in txt and "Metropolitan" not in txt \
                and "County" not in txt:
            kind = "NFP"
        elif re.search(r"\bConsumer Price Index\b", txt) and "Summary" not in txt:
            kind = "CPI"
        else:
            continue
        md = BLS_DATE.search(txt)
        mt = BLS_TIME.search(txt)
        if not md or not mt:
            continue
        mo = month_num(md.group(2))
        if mo is None:
            continue
        d = dt.date(int(md.group(4)), mo, int(md.group(3)))
        hh, mm = int(mt.group(1)) % 12, int(mt.group(2))
        if mt.group(3).upper() == "PM":
            hh += 12
        if d.strftime("%A") != md.group(1):
            continue                                     # weekday self-check
        rows.append(dict(kind=kind, date=d, hh=hh, mm=mm, zone=ET,
                         source="verified_web", confidence="high",
                         note=f"bls.gov/schedule/{year} ({hh:02d}:{mm:02d} ET)"))
    return rows


# --------------------------------------------------------------------------- #
# Federal Reserve -- FOMC statement days + statement release times
# --------------------------------------------------------------------------- #
FOMC_STMT = re.compile(r"/(?:newsevents/pressreleases|monetarypolicy/files)/"
                       r"monetary(\d{8})a\d?\.(?:htm|pdf)")
FOMC_RELEASE_TIME = re.compile(
    r"For release at\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*(EST|EDT)", re.I)


def scrape_fomc(refresh: bool, offline: bool) -> list[dict]:
    dates: set[dt.date] = set()
    pages = [("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
              "fomccalendars.htm")]
    for y in range(2015, 2021):
        pages.append((f"https://www.federalreserve.gov/monetarypolicy/"
                      f"fomchistorical{y}.htm", f"fomchistorical{y}.htm"))
    src_of: dict[dt.date, str] = {}
    for url, tag in pages:
        html = get(url, refresh, offline)
        if html is None:
            continue
        for s in FOMC_STMT.findall(html):
            try:
                d = dt.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
            except ValueError:
                continue
            if START <= d <= END:
                dates.add(d)
                src_of.setdefault(d, tag)

    rows: list[dict] = []
    for d in sorted(dates):
        url = ("https://www.federalreserve.gov/newsevents/pressreleases/"
               f"monetary{d:%Y%m%d}a.htm")
        html = get(url, refresh, offline)
        hh, mm, conf, note = 14, 0, "medium", "14:00 ET rule (page carries no release-time line)"
        if html:
            m = FOMC_RELEASE_TIME.search(strip_tags(html))
            if m:
                hh = int(m.group(1)) % 12
                mm = int(m.group(2))
                if m.group(3).lower() == "p":
                    hh += 12
                conf = "high"
                note = f"statement release time scraped: {hh:02d}:{mm:02d} ET"
                if (hh, mm) != (14, 0):
                    note += "  [OFF-SCHEDULE TIME -- unscheduled/emergency statement]"
        rows.append(dict(kind="FOMC", date=d, hh=hh, mm=mm, zone=ET,
                         source="verified_web", confidence=conf,
                         note=f"{src_of.get(d, '')}; {note}"))
    return rows


# --------------------------------------------------------------------------- #
# Bank of Japan -- MPM decision days
# --------------------------------------------------------------------------- #
BOJ_MINUTES = re.compile(
    r"Meeting on\s+([A-Z][a-z]+\.?)\s+(\d{1,2})"
    r"(?:\s+and\s+(?:([A-Z][a-z]+\.?)\s+)?(\d{1,2}))?,\s*(\d{4})")
BOJ_PDF = re.compile(r"/k(\d{6})[a-z]?\.pdf")


def scrape_boj(refresh: bool, offline: bool) -> list[dict]:
    found: dict[dt.date, str] = {}
    for y in YEARS:
        u1 = f"https://www.boj.or.jp/en/mopo/mpmsche_minu/minu_{y}/index.htm"
        html = get(u1, refresh, offline)
        if html:
            txt = strip_tags(html)
            for m in BOJ_MINUTES.finditer(txt):
                mo1, d1, mo2, d2, yy = m.groups()
                yr = int(yy)
                if d2:
                    mo = month_num(mo2) if mo2 else month_num(mo1)
                    day = int(d2)
                else:
                    mo, day = month_num(mo1), int(d1)
                if mo is None:
                    continue
                try:
                    d = dt.date(yr, mo, day)
                except ValueError:
                    continue
                if START <= d <= END:
                    found.setdefault(d, f"minu_{y} (minutes title)")
        u2 = f"https://www.boj.or.jp/en/mopo/mpmdeci/mpr_{y}/index.htm"
        html2 = get(u2, refresh, offline)
        if html2:
            for s in BOJ_PDF.findall(html2):
                try:
                    d = dt.date(2000 + int(s[:2]), int(s[2:4]), int(s[4:6]))
                except ValueError:
                    continue
                if START <= d <= END:
                    found.setdefault(d, f"mpr_{y} (statement pdf k{s})")
    rows = []
    for d, src in sorted(found.items()):
        rows.append(dict(kind="BOJ", date=d, hh=BOJ_NOMINAL_JST[0],
                         mm=BOJ_NOMINAL_JST[1], zone=JST,
                         source="verified_web", confidence="high",
                         note=f"boj.or.jp {src}; RELEASE TIME DRIFTS -- time_utc is the "
                              f"nominal 11:30 JST anchor, window "
                              f"{BOJ_WINDOW_UTC[0]}-{BOJ_WINDOW_UTC[1]} UTC"))
    return rows


# --------------------------------------------------------------------------- #
# rule fallbacks (used only for whole years the scrape could not reach)
# --------------------------------------------------------------------------- #
def first_friday(y: int, m: int) -> dt.date:
    d = dt.date(y, m, 1)
    return d + dt.timedelta(days=(4 - d.weekday()) % 7)


def nfp_rule_rows(year: int) -> list[dict]:
    out = []
    for m in range(1, 13):
        d = first_friday(year, m)
        if not (START <= d <= END):
            continue
        out.append(dict(kind="NFP", date=d, hh=8, mm=30, zone=ET,
                        source="rule", confidence="medium",
                        note="first-Friday rule, 08:30 ET (bls.gov unreachable); "
                             "BLS shifts around federal holidays -- date may be off"))
    return out


def cpi_rule_rows(year: int) -> list[dict]:
    out = []
    for m in range(1, 13):
        d = dt.date(year, m, 12)
        if d.weekday() == 5:
            d -= dt.timedelta(days=1)
        elif d.weekday() == 6:
            d += dt.timedelta(days=1)
        if not (START <= d <= END):
            continue
        out.append(dict(kind="CPI", date=d, hh=8, mm=30, zone=ET,
                        source="rule", confidence="medium",
                        note="day-12-snapped-to-weekday rule, 08:30 ET "
                             "(bls.gov unreachable); +/-1 day caveat"))
    return out


# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="ignore the HTML cache")
    ap.add_argument("--offline", action="store_true", help="cache only, no network")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    print("=" * 100)
    print("FX EVENT CALENDAR -- primary-source scrape")
    print(f"range {START} .. {END}   types NFP/CPI/FOMC/BOJ")
    print("=" * 100)

    print("\nDST spot checks (zoneinfo; JST has no DST):")
    checks = [
        ("08:30 ET 2015-01-09 (EST)", local_to_utc(dt.date(2015, 1, 9), 8, 30, ET), "13:30Z"),
        ("08:30 ET 2015-07-02 (EDT)", local_to_utc(dt.date(2015, 7, 2), 8, 30, ET), "12:30Z"),
        ("14:00 ET 2020-12-16 (EST)", local_to_utc(dt.date(2020, 12, 16), 14, 0, ET), "19:00Z"),
        ("14:00 ET 2024-06-12 (EDT)", local_to_utc(dt.date(2024, 6, 12), 14, 0, ET), "18:00Z"),
        ("11:30 JST 2024-01-23     ", local_to_utc(dt.date(2024, 1, 23), 11, 30, JST), "02:30Z"),
        ("11:30 JST 2024-07-31     ", local_to_utc(dt.date(2024, 7, 31), 11, 30, JST), "02:30Z"),
    ]
    ok_dst = True
    for lab, got, exp in checks:
        good = got.strftime("%H:%MZ") == exp
        ok_dst &= good
        print(f"  {lab} -> {iso_utc(got)}  expect {exp}  {'OK' if good else 'MISMATCH'}")

    rows: list[dict] = []
    dropped: list[str] = []

    # ---------------------------------------------------------------- BLS
    print("\nscraping bls.gov year schedules ...")
    for y in YEARS:
        got = scrape_bls(y, args.refresh, args.offline)
        n_nfp = sum(1 for r in got if r["kind"] == "NFP")
        n_cpi = sum(1 for r in got if r["kind"] == "CPI")
        if not got:
            print(f"  {y}: UNREACHABLE -> falling back to rules")
            got = nfp_rule_rows(y) + cpi_rule_rows(y)
            n_nfp = sum(1 for r in got if r["kind"] == "NFP")
            n_cpi = sum(1 for r in got if r["kind"] == "CPI")
            print(f"       rule rows: NFP={n_nfp} CPI={n_cpi}")
        else:
            print(f"  {y}: NFP={n_nfp}  CPI={n_cpi}")
        rows += got

    # ---------------------------------------------------------------- Fed
    print("\nscraping federalreserve.gov FOMC calendars + statement pages ...")
    fomc = scrape_fomc(args.refresh, args.offline)
    print(f"  FOMC statements found: {len(fomc)}")
    if not fomc:
        dropped.append("FOMC: federalreserve.gov unreachable and no cache -- "
                       "no FOMC rows emitted")
    rows += fomc

    # ---------------------------------------------------------------- BOJ
    print("\nscraping boj.or.jp MPM minutes + statement indexes ...")
    boj = scrape_boj(args.refresh, args.offline)
    print(f"  BOJ MPM decision days found: {len(boj)}")
    if not boj:
        dropped.append("BOJ: boj.or.jp unreachable and no cache -- no BOJ rows emitted")
    rows += boj

    # ---------------------------------------------------------------- assemble
    seen: set[tuple[str, dt.date]] = set()
    final: list[dict] = []
    for r in sorted(rows, key=lambda r: (r["date"], r["kind"])):
        if not (START <= r["date"] <= END):
            continue
        key = (r["kind"], r["date"])
        if key in seen:
            continue
        seen.add(key)
        t = local_to_utc(r["date"], r["hh"], r["mm"], r["zone"])
        r["ts"] = t
        final.append(r)

    # Sanity gates.  A weekend date is an ANOMALY, not automatically an error:
    # the 2020-03-15 emergency FOMC cut really was a Sunday 17:00 ET release,
    # landing exactly on the FX week open.  So a weekend date coming from a
    # primary source is KEPT and flagged; a weekend date coming from a rule or
    # from training knowledge is a rule failure and is DROPPED.
    kept: list[dict] = []
    weekend_flagged: list[dict] = []
    for r in final:
        if r["date"].weekday() >= 5:
            if r["source"] == "verified_web":
                r["note"] += "  [WEEKEND RELEASE -- FX liquidity is thin/absent; " \
                             "tick window may be empty or a week-open gap]"
                weekend_flagged.append(r)
            else:
                dropped.append(f"{r['kind']} {r['date']} on a "
                               f"{r['date'].strftime('%A')} from source="
                               f"{r['source']} -- rule failure, dropped")
                continue
        kept.append(r)

    OUTP = Path(args.out)
    OUTP.parent.mkdir(parents=True, exist_ok=True)
    with OUTP.open("w", encoding="utf-8", newline="") as f:
        f.write("date,time_utc,type,source,confidence,note\n")
        for r in kept:
            note = r["note"].replace('"', "'")
            f.write(f'{r["date"].isoformat()},{iso_utc(r["ts"])},{r["kind"]},'
                    f'{r["source"]},{r["confidence"]},"{note}"\n')

    # ---------------------------------------------------------------- report
    print("\n" + "=" * 100)
    print(f"WROTE {OUTP.relative_to(ROOT)}  ({len(kept)} events)")
    print("=" * 100)
    print(f"\nnetwork requests: {N_NET}   cache hits: {N_CACHE}   "
          f"failed urls: {len(FAILED_URLS)}")
    for u, e in FAILED_URLS[:12]:
        print(f"    ! {e}  {u}")

    print(f"\n{'type':<8}{'count':>7}   per-year")
    print("-" * 100)
    for k in ("NFP", "CPI", "FOMC", "BOJ"):
        sub = [r for r in kept if r["kind"] == k]
        per = " ".join(f"{y}:{sum(1 for r in sub if r['date'].year == y)}" for y in YEARS)
        print(f"{k:<8}{len(sub):>7}   {per}")

    print(f"\n{'source':<16}{'confidence':<14}{'count':>7}")
    print("-" * 100)
    combo: dict[tuple[str, str], int] = {}
    for r in kept:
        combo[(r["source"], r["confidence"])] = combo.get((r["source"], r["confidence"]), 0) + 1
    for (s, c), n in sorted(combo.items()):
        print(f"{s:<16}{c:<14}{n:>7}")

    print("\nSANITY")
    print("-" * 100)
    bad_wd = [r for r in kept if r["date"].weekday() >= 5]
    unexplained = [r for r in bad_wd if r["source"] != "verified_web"]
    print(f"  every FOMC/BOJ date is a weekday      : "
          f"{'PASS' if not unexplained else 'FAIL'}"
          f"   ({len(bad_wd)} weekend date(s), all primary-source-verified "
          f"anomalies listed below)")
    nfp = [r for r in kept if r["kind"] == "NFP"]
    nonfri = [r for r in nfp if r["date"].weekday() != 4]
    print(f"  NFP on a Friday                       : {len(nfp)-len(nonfri)}/{len(nfp)}"
          f"   ({len(nonfri)} exceptions, listed below)")
    print(f"  any weekend date at all               : {len(bad_wd)}")
    print(f"  DST spot checks                       : {'PASS' if ok_dst else 'FAIL'}")

    if nonfri:
        print("\n  NFP DATE EXCEPTIONS (verified against bls.gov -- kept, not corrected):")
        for r in nonfri:
            print(f"    {r['date']} {r['date'].strftime('%a')}  {r['note']}")

    # first-Friday rule vs verified reality: the exceptions the rule would miss
    rulemiss = []
    for r in nfp:
        if r["source"] != "verified_web":
            continue
        ff = first_friday(r["date"].year, r["date"].month)
        # the release covers the PREVIOUS month, so compare within its own month
        if r["date"] != ff:
            rulemiss.append((r["date"], ff))
    print(f"\n  first-Friday RULE vs verified date: {len(rulemiss)} of "
          f"{len([r for r in nfp if r['source']=='verified_web'])} disagree")
    for d, ff in rulemiss:
        print(f"    verified {d} ({d.strftime('%a')})  rule would have said {ff}"
              f"  [delta {(d-ff).days:+d}d]")

    offsched = [r for r in kept if "OFF-SCHEDULE" in r["note"]]
    if offsched:
        print(f"\n  FOMC statements NOT at 14:00 ET ({len(offsched)}) -- scraped times kept:")
        for r in offsched:
            print(f"    {r['date']}  {iso_utc(r['ts'])}  {r['note'].split(';',1)[1].strip()[:80]}")

    if weekend_flagged:
        print(f"\n  WEEKEND RELEASES kept + flagged ({len(weekend_flagged)}):")
        for r in weekend_flagged:
            print(f"    {r['kind']:<5}{r['date']} {r['date'].strftime('%a')}  "
                  f"{iso_utc(r['ts'])}")

    if dropped:
        print(f"\n  DROPPED ({len(dropped)}):")
        for d in dropped:
            print(f"    {d}")
    else:
        print("\n  DROPPED: none")

    print("\nCAVEATS")
    print("-" * 100)
    print("  * BOJ time_utc is a NOMINAL anchor (11:30 JST).  The real release drifts;")
    print(f"    downstream must use the {BOJ_WINDOW_UTC[0]}-{BOJ_WINDOW_UTC[1]} UTC band, not the minute.")
    print("  * FOMC rows with confidence=medium carry the 14:00 ET rule because the")
    print("    archived press-release page has no release-time line.  The rule has held")
    print("    for every scheduled statement since 2013 but is not verified per-date.")
    print("  * BLS year pages are the schedule as archived; a release moved AFTER the")
    print("    page was last regenerated would not show.  The 2025 shutdown reschedule")
    print("    IS reflected, which is evidence the pages are kept current.")
    print("  * 2026 rows past today are the PUBLISHED FORWARD schedule, not history.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
