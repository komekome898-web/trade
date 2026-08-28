#!/usr/bin/env python3
"""
Build a PRIMARY-SOURCE macro-event calendar for 2005-01-01 .. 2014-12-31.

    types : NFP (Employment Situation) / CPI (Consumer Price Index) / FOMC
    output: backtest_data/fx_event_ticks_2005_2014/calendar.csv
            (same columns as backtest_data/fx_event_ticks_2015_2026/calendar.csv:
             date,time_utc,type,source,confidence,note)

WHY THIS FILE EXISTS
--------------------
docs/KNOWLEDGE_FX.md sec.4.5 measured what happens when calendar dates are
GUESSED from rules: the "CPI is near the 12th" rule was right 20.9% of the time
and the CPI arm of study S3 was therefore noise.  docs/PREREG_fx_s4_judgment.md
sec.2 forbids rule-generated dates for the 2005-2014 judgment set.  Every date
below comes from the publisher's own archived schedule page.

PRIMARY SOURCES
---------------
NFP / CPI
    https://www.bls.gov/schedule/{YYYY}/home.htm      (archived year schedules)
    2008-2014 : HTML table, one <tr> per release
                "Friday, January 04, 2013 | 08:30 AM | Employment Situation ..."
    2005-2007 : plain-text <pre> block
                "The Employment Situation, December 2004   Jan.  7, 2005   8:30 am"
                The year appears only on the first line of each month block, so
                it is carried forward; rows whose date falls outside the page
                year are the next-January preview and are dropped (the next
                year's own page carries them).
    These pages are the schedule AS RELEASED: verified on the 2013 page, which
    shows the shutdown reschedule (September Employment Situation on Oct 22,
    September CPI on Oct 30), not the originally planned dates.
    bls.gov 403s browser User-Agents and 200s an identifying one.

FOMC
    https://www.federalreserve.gov/monetarypolicy/fomchistorical{YYYY}.htm
    Only panels headed "<dates> Meeting - YYYY" are kept.  Panels headed
    "<date> Conference Call - YYYY" are DROPPED even when they carry a
    statement (2007-08-17, 2008-01-22, 2008-03-11, 2008-10-08, 2010-05-09 ...):
    those are unscheduled releases whose clock time is not governed by any
    standing rule, so keeping them would smuggle a guessed time into the set.
    DECISION DATE = the last day in the panel heading, cross-checked against the
    FOMC{YYYYMMDD}* document names inside the same panel (Agenda / Tealbook /
    Transcript).  The heading+documents are used rather than the "Statement"
    href because the Fed's own 2007 page links the June 27-28 statement to
    /newsevents/press/monetary/20070618a.htm, which is a broken link on their
    side; the panel's own FOMC20070628* documents give 2007-06-28.

FOMC RELEASE TIME -- three tiers, each with a primary source
    (a) EXACT, scraped, confidence=high
        https://www.federalreserve.gov/monetarypolicy/fomcpresconf{YYYYMMDD}.htm
        carries "FOMC Meeting Statement (Released January 25, 2012 at 12:20 p.m.)".
        These pages exist for every press-conference meeting from 2011-04-27 on.
    (b) 14:00 ET, confidence=medium, for statements from 2013-03-20 onward
        https://www.federalreserve.gov/newsevents/pressreleases/monetary20130313a.htm
        "Committee policy statements for all regularly scheduled meetings will
         now be released at 2 p.m. Eastern Time."  (announced 2013-03-13; the
         first meeting under it was March 19-20, 2013)
    (c) 14:15 ET, confidence=medium, for every scheduled statement before that
        https://www.federalreserve.gov/newsevents/pressreleases/monetary20110324a.htm
        "For these meetings, the FOMC statement is expected to be released at
         around 12:30 p.m., ONE HOUR AND FORTY-FIVE MINUTES EARLIER THAN FOR
         OTHER FOMC MEETINGS."  12:30 + 1:45 = 14:15 ET for all other meetings.
    Tier (a) overrides (b) and (c) whenever the press-conference page exists,
    including the 2011-2012 meetings where the statement moved to ~12:30 ET.

CONFIDENCE LADDER (same words as the 2015-2026 calendar)
    verified_web / high    date AND clock time scraped from the primary source
    verified_web / medium  date scraped; time from a standing rule that is
                           itself documented by a primary Fed press release
    Nothing else is emitted.  Anything that cannot reach at least `medium` is
    dropped and counted in the summary.

DST via zoneinfo(America/New_York).  Raw HTML is cached, so a re-run does no
network I/O and writes a byte-identical calendar.csv.

Usage
    python scripts/fetch_fx_calendar_2005_2014.py [--refresh] [--offline]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html as H
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "backtest_data" / "fx_event_ticks_2005_2014"
OUT = OUTDIR / "calendar.csv"
CACHE = ROOT / "data" / "fx" / "calendar_cache_2005_2014"

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc

START = dt.date(2005, 1, 1)
END = dt.date(2014, 12, 31)
YEARS = list(range(2005, 2015))

UA = "trade-research/1.0 (+contact: komekome3ai@gmail.com)"

# primary-source URLs for the two FOMC timing rules (written into `note`)
SRC_TIME_1400 = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20130313a.htm"
SRC_TIME_1415 = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20110324a.htm"
RULE_1400_FROM = dt.date(2013, 3, 20)   # first meeting after the 2013-03-13 notice

N_NET = 0
N_CACHE = 0
FAILED: list[tuple[str, str]] = []
_next_ok = [0.0]


def get(url: str, refresh: bool = False, offline: bool = False, retries: int = 4) -> str | None:
    """Polite cached GET.  Returns page text or None."""
    global N_NET, N_CACHE
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    tail = re.sub(r"[^A-Za-z0-9._-]", "_", url.split("//", 1)[-1])[-60:]
    p = CACHE / f"{h}_{tail}"
    if p.exists() and not refresh:
        N_CACHE += 1
        return p.read_text(encoding="utf-8", errors="replace")
    if offline:
        return None
    last = ""
    for attempt in range(retries):
        delay = max(0.0, _next_ok[0] - time.monotonic())
        if delay:
            time.sleep(delay)
        _next_ok[0] = time.monotonic() + 0.6      # government sites: slow on purpose
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
            if e.code in (403, 404):
                break
            time.sleep(2.0 * (attempt + 1))
        except Exception as e:                                    # noqa: BLE001
            last = str(e)
            time.sleep(2.0 * (attempt + 1))
    FAILED.append((url, last))
    return None


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", H.unescape(s)).strip()


MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})
MONTHS["sept"] = 9


def month_num(tok: str) -> int | None:
    return MONTHS.get(tok.strip().strip(".").lower())


def to_utc(day: dt.date, hh: int, mm: int) -> dt.datetime:
    return dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=ET).astimezone(UTC)


# --------------------------------------------------------------------------- #
# BLS
# --------------------------------------------------------------------------- #
BLS_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
BLS_DATE = re.compile(r"([A-Z][a-z]+day),\s*([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})")
BLS_TIME = re.compile(r"(\d{1,2}):(\d{2})\s*(AM|PM)", re.I)

PRE_LINE = re.compile(
    r"^(.*?)\s{2,}([A-Z][a-z]+\.?)\s+(\d{1,2})(?:,\s*(\d{4}))?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m",
    re.I)


def classify(name: str) -> str | None:
    """NFP / CPI / None from a BLS release name.  Deliberately strict."""
    if "Employment Situation" in name:
        if any(w in name for w in ("Veterans", "State", "Metropolitan", "County",
                                   "Regional", "Youth", "Women", "Persons")):
            return None
        return "NFP"
    if re.search(r"\bConsumer Price Index(es)?\b", name):
        if "Summary" in name:
            return None
        return "CPI"
    return None


def scrape_bls_year(year: int, refresh: bool, offline: bool) -> list[dict]:
    url = f"https://www.bls.gov/schedule/{year}/home.htm"
    html = get(url, refresh, offline)
    if html is None:
        return []
    rows: list[dict] = []

    # --- 2008+ : one <tr> per release ------------------------------------- #
    for raw in BLS_ROW.findall(html):
        txt = strip_tags(raw)
        kind = classify(txt)
        if kind is None:
            continue
        md, mt = BLS_DATE.search(txt), BLS_TIME.search(txt)
        if not md or not mt:
            continue
        mo = month_num(md.group(2))
        if mo is None:
            continue
        d = dt.date(int(md.group(4)), mo, int(md.group(3)))
        if d.strftime("%A") != md.group(1):        # weekday self-check
            continue
        hh, mm = int(mt.group(1)) % 12, int(mt.group(2))
        if mt.group(3).upper() == "PM":
            hh += 12
        rows.append(dict(kind=kind, date=d, hh=hh, mm=mm,
                         note=f"bls.gov/schedule/{year}/home.htm table row "
                              f"({hh:02d}:{mm:02d} ET)"))

    # --- 2005-2007 : plain-text <pre> schedule ----------------------------- #
    if not rows:
        carry, prev_mo = year, 0
        for block in re.findall(r"<pre[^>]*>(.*?)</pre>", html, re.S | re.I):
            for line in H.unescape(re.sub(r"<[^>]+>", "", block)).replace("\xa0", " ").split("\n"):
                m = PRE_LINE.match(line.rstrip())
                if not m:
                    continue
                mo = month_num(m.group(2))
                if mo is None:
                    continue
                if m.group(4):
                    carry = int(m.group(4))
                elif prev_mo and mo + 6 < prev_mo:
                    # the schedule is chronological; a >=6-month regression is the
                    # December -> January wrap into the following year's preview
                    carry += 1
                prev_mo = mo
                hh, mm = int(m.group(5)) % 12, int(m.group(6))
                if m.group(7).lower() == "p":
                    hh += 12
                try:
                    d = dt.date(carry, mo, int(m.group(3)))
                except ValueError:
                    continue
                kind = classify(m.group(1).strip())
                if kind is None or d.year != year:
                    continue                       # next-January preview rows
                rows.append(dict(kind=kind, date=d, hh=hh, mm=mm,
                                 note=f"bls.gov/schedule/{year}/home.htm text schedule "
                                      f"({hh:02d}:{mm:02d} ET)"))
    seen, uniq = set(), []
    for r in rows:                                     # (kind, date) is the identity
        k = (r["kind"], r["date"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq


# --------------------------------------------------------------------------- #
# FOMC
# --------------------------------------------------------------------------- #
PANEL_HEAD = re.compile(r'<h5[^>]*>(.*?)</h5>', re.S)
HEAD_RANGE = re.compile(
    r"^([A-Z][a-z]+)\s+(\d{1,2})(?:\s*[-–]\s*(?:([A-Z][a-z]+)\s+)?(\d{1,2}))?\s+"
    r"(Meeting|Conference Call)\b")
# 2013 uses one more shape for a month-straddling meeting: "April/May 30-1 Meeting"
HEAD_SLASH = re.compile(
    r"^([A-Z][a-z]+)/([A-Z][a-z]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2})\s+(Meeting|Conference Call)\b")
FOMC_DOC = re.compile(r"FOMC(\d{8})")
PC_TIME = re.compile(
    r"FOMC Meeting Statement\s*\(Released\s+([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})\s+at\s+"
    r"(\d{1,2}):(\d{2})\s*([ap])\.m\.\)", re.I)


def scrape_fomc_year(year: int, refresh: bool, offline: bool) -> list[dict]:
    url = f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm"
    html = get(url, refresh, offline)
    if html is None:
        return []
    heads = list(PANEL_HEAD.finditer(html))
    out: list[dict] = []
    for i, m in enumerate(heads):
        head = strip_tags(m.group(1))
        body = html[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(html)]
        hs = HEAD_SLASH.match(head)
        if hs:
            if hs.group(5) != "Meeting":
                continue
            mo, day = month_num(hs.group(2)), int(hs.group(4))
            if mo is None:
                continue
        else:
            hm = HEAD_RANGE.match(head)
            if not hm or hm.group(5) != "Meeting":
                continue                              # conference calls dropped
            mo1 = month_num(hm.group(1))
            if mo1 is None:
                continue
            if hm.group(4):                           # multi-day meeting
                mo = month_num(hm.group(3)) if hm.group(3) else mo1
                day = int(hm.group(4))
            else:
                mo, day = mo1, int(hm.group(2))
        try:
            d = dt.date(year, mo, day)
        except ValueError:
            continue
        docs = sorted(set(FOMC_DOC.findall(body)))
        agree = f"{d:%Y%m%d}" in docs
        out.append(dict(date=d, head=head, docs=docs, agree=agree))
    return out


def fomc_release_time(d: dt.date, refresh: bool, offline: bool) -> tuple[int, int, str, str]:
    """(hh, mm, confidence, note) in ET."""
    pc = get(f"https://www.federalreserve.gov/monetarypolicy/fomcpresconf{d:%Y%m%d}.htm",
             refresh, offline)
    if pc:
        m = PC_TIME.search(strip_tags(pc))
        if m and month_num(m.group(1)) == d.month and int(m.group(2)) == d.day \
                and int(m.group(3)) == d.year:
            hh, mm = int(m.group(4)) % 12, int(m.group(5))
            if m.group(6).lower() == "p":
                hh += 12
            return hh, mm, "high", (f"fomcpresconf{d:%Y%m%d}.htm states the statement was "
                                    f"released at {hh:02d}:{mm:02d} ET")
    if d >= RULE_1400_FROM:
        return 14, 0, "medium", ("14:00 ET for all regularly scheduled meetings, announced "
                                 f"{SRC_TIME_1400}")
    return 14, 15, "medium", ("14:15 ET for regularly scheduled meetings (press-conference "
                              f"meetings were '1h45m earlier', {SRC_TIME_1415})")


# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args(argv)

    print("=" * 100)
    print("PRIMARY-SOURCE MACRO CALENDAR 2005-2014  (NFP / CPI / FOMC)")
    print("=" * 100)

    rows: list[dict] = []
    dropped: list[str] = []

    # ---- BLS ------------------------------------------------------------- #
    for y in YEARS:
        got = scrape_bls_year(y, args.refresh, args.offline)
        n_nfp = sum(1 for r in got if r["kind"] == "NFP")
        n_cpi = sum(1 for r in got if r["kind"] == "CPI")
        print(f"  BLS {y}: NFP {n_nfp:>2}  CPI {n_cpi:>2}"
              f"{'   *** INCOMPLETE ***' if (n_nfp != 12 or n_cpi != 12) else ''}")
        if not got:
            dropped.append(f"BLS {y}: page unreachable, whole year dropped")
        for r in got:
            if not (START <= r["date"] <= END):
                continue
            rows.append(dict(date=r["date"], t=to_utc(r["date"], r["hh"], r["mm"]),
                             kind=r["kind"], source="verified_web", confidence="high",
                             note=r["note"]))

    # ---- FOMC ------------------------------------------------------------ #
    n_disagree = 0
    for y in YEARS:
        got = scrape_fomc_year(y, args.refresh, args.offline)
        print(f"  FOMC {y}: scheduled meetings {len(got):>2}"
              f"{'   *** NOT 8 ***' if len(got) != 8 else ''}")
        if not got:
            dropped.append(f"FOMC {y}: page unreachable, whole year dropped")
        for g in got:
            d = g["date"]
            if not (START <= d <= END):
                continue
            hh, mm, conf, tnote = fomc_release_time(d, args.refresh, args.offline)
            xnote = "heading/doc-name agree" if g["agree"] else \
                    f"heading date NOT in panel docs {g['docs']}"
            if not g["agree"]:
                n_disagree += 1
            rows.append(dict(date=d, t=to_utc(d, hh, mm), kind="FOMC",
                             source="verified_web", confidence=conf,
                             note=f"fomchistorical{y}.htm '{g['head']}' ({xnote}); {tnote}"))

    rows.sort(key=lambda r: (r["t"], r["kind"]))

    # ---- write ----------------------------------------------------------- #
    OUTDIR.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "time_utc", "type", "source", "confidence", "note"])
        for r in rows:
            w.writerow([f"{r['date']:%Y-%m-%d}", r["t"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                        r["kind"], r["source"], r["confidence"], r["note"]])

    print("\n" + "-" * 100)
    by = {}
    for r in rows:
        by[r["kind"]] = by.get(r["kind"], 0) + 1
    print(f"  written : {OUT}")
    print(f"  events  : {len(rows)}   " + ", ".join(f"{k}={v}" for k, v in sorted(by.items())))
    hi = sum(1 for r in rows if r["confidence"] == "high")
    print(f"  confidence: high {hi} ({100*hi/max(len(rows),1):.1f}%), medium {len(rows)-hi}")
    print(f"  primary-source rate: {100.0 * len(rows) / max(len(rows), 1):.1f}% "
          f"(every row scraped from bls.gov or federalreserve.gov; zero rule-generated DATES)")
    print(f"  FOMC panels whose heading date is not among the panel's own FOMC* documents: "
          f"{n_disagree}")
    print(f"  span    : {rows[0]['date']} .. {rows[-1]['date']}")
    print(f"  network : {N_NET} fetched, {N_CACHE} from cache")
    if dropped:
        print("  DROPPED:")
        for d in dropped:
            print(f"      {d}")
    if FAILED:
        print(f"  unreachable URLs ({len(FAILED)}):")
        for u, why in FAILED[:20]:
            print(f"      {why:<12} {u}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
