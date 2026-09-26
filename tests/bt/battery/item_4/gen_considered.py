#!/usr/bin/env python3
"""Write tests/bt/battery/item_4/opponents/CONSIDERED.md (the review table of the candidates that could not be run)
and opponents/RUNNABILITY.tsv (what was tried for every candidate).

    python3 tests/bt/battery/item_4/gen_considered.py
    python3 scripts/check_bt_considered.py tests/bt/battery/item_4/opponents/CONSIDERED.md --write

Candidates = what REQUIREMENTS.md §3 extracted, nothing added or removed: none for I4-1..I4-4 (§3.1), the four named
in §3.2 for I4-5 (121, 21, 93, hftbacktest = catalogue 23) and I4-6 (75, 19, 8, 12), the 55 rows with 足 = ○ for
I4-8..I4-18 (§3.3), and none for I4-7 / I4-19 / I4-20 (§3.4).  For each viewpoint:
- a candidate that runs in an isolated venv is 「動かせた」 when at least one of the viewpoint's scenes ended in
  something other than 「結果なし」 in survey_results/<target>.tsv (counted here, never typed); otherwise it gets a row
  「持たないと確認した」 whose reason is what its adapter found when the scenes were run;
- a candidate reproduced from its primary source (opponents/repro_*.py) gets 「再現した」 where the reproduction
  returned a result, and otherwise 「持たないと確認した」 (the reproduction's reason cites the source lines) or
  「再現できない」 when every scene of the viewpoint stopped at a part of the source that was not read ("再現していない");
- a candidate neither run nor reproduced gets the judgement in NOT_RUN ((b) read, or (a) only for the survey's 11
  dangerous candidates).
The aggregate block is written by scripts/check_bt_considered.py --write, not here.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import i4_scenes as S  # noqa: E402
import i4_targets as T  # noqa: E402

RES = HERE / "survey_results"
OUT = HERE / "opponents" / "CONSIDERED.md"
RUNTSV = HERE / "opponents" / "RUNNABILITY.tsv"

POOL_BARS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 13, 15, 16, 18, 19, 20, 21, 40, 43, 44, 45, 46, 48, 50, 51, 52, 53, 54, 55,
             56, 57, 58, 60, 61, 62, 67, 68, 69, 70, 72, 73, 74, 75, 80, 85, 86, 87, 92, 94, 107, 111, 120, 121, 122, 123]
POOL = {"I4-5": [121, 21, 93, 23], "I4-6": [75, 19, 8, 12]}
for v in ("I4-8", "I4-9", "I4-10", "I4-11", "I4-12", "I4-13", "I4-14", "I4-15", "I4-16", "I4-17", "I4-18"):
    POOL[v] = POOL_BARS
ZERO = {
    "I4-1": "`grep -inE 'reference implementation|golden (test|file|output)|known.?answer|known.?good' SCAN_clean.md`(REQUIREMENTS.md §3.1、当たり 0 件)",
    "I4-2": "`grep -inE 'property.?(based|test)|hypothesis' SCAN_clean.md` / `grep -inE 'プロパティベース|プロパティテスト|ハイポセシス' SCAN_clean.md`(REQUIREMENTS.md §3.1、当たり 2 件はどちらも候補 105 の開発用の依存の一覧で、道具の機構ではないので 0 件)",
    "I4-3": "`grep -inE 'reference implementation|golden (test|file|output)|known.?answer|known.?good' SCAN_clean.md`(REQUIREMENTS.md §3.1、I4-1 と同じ語、当たり 0 件)",
    "I4-4": "`grep -inE 'verified against|等価性|drop-in replacement|API.?compatib' SCAN_clean.md` / `grep -inE 'cross.?check|クロスチェック|benchmark against|答え合わせ' SCAN_clean.md` / `grep -inE 'regression test|test vector|テストベクタ' SCAN_clean.md`(REQUIREMENTS.md §3.1、当たり 0 / 0 / 0 件)",
    "I4-7": "`REQUIREMENTS.md §3.4(内部制約の観点。SCAN に語を探していない。場面にもしていない: DEFINITIONS.md「場面にできない観点」)`",
    "I4-19": "`REQUIREMENTS.md §3.4(内部制約の観点。SCAN に語を探していない。場面にもしていない: DEFINITIONS.md「場面にできない観点」)`",
    "I4-20": "`REQUIREMENTS.md §3.4(内部制約の観点。SCAN に語を探していない。場面にもしていない: DEFINITIONS.md「場面にできない観点」)`",
}

NAMES = {1: "Basana", 2: "Backtrader", 3: "PySystemtrade", 4: "PyBroker", 5: "Lean CLI", 6: "Ziplime", 7: "Superalgos",
         8: "OpenTrader", 10: "fast-trade", 11: "python3(台帳の名。SCAN 8452 行は OctoBot)", 12: "pybotters",
         13: "DeviaVir/zenbot", 15: "Mendl-Labs/BacktestingCore", 16: "Luczinsritter/event_driven_backtesting_engine",
         18: "zipline-reloaded", 19: "Jesse", 20: "VnPy", 21: "Qlib", 23: "hftbacktest", 40: "OpenMarket",
         43: "QuantDinger", 44: "lo2cin4", 45: "ForexTester", 46: "MT4裁量トレード練習君プレミアム", 48: "BacktestingMax",
         50: "AlgoTest", 51: "QUANTAXIS", 52: "QuantConnect", 53: "Rqalpha", 54: "finmarketpy", 55: "backtesting.py",
         56: "zvt", 57: "WonderTrader", 58: "nautilus_trader", 60: "Hikyuu", 61: "barter-rs", 62: "qf-lib", 67: "lumibot",
         68: "quanttrader", 69: "gobacktest", 70: "PineForge", 72: "QTradeX", 73: "vectorbt", 74: "ml-quant-trading",
         75: "Freqtrade", 80: "Hummingbot", 85: "czsc", 86: "analyzingalpha", 87: "PyTrendFollow",
         92: "prediction-market-backtester", 93: "punyamodi/binary_market_engine", 94: "mote/backtest", 107: "sigc",
         111: "HKUDS/Vibe-Trading", 120: "wbt", 121: "mhallsmoore/qstrader", 122: "gbeced/pyalgotrade",
         123: "carlos8f/zenbot"}

# the mechanism column (one line per candidate, from the adapter / reproduction docstrings and the survey report)
MECH = {
    1: "事象駆動の暗号資産の枠組み(Decimal の値、足の事象で約定)", 2: "事象駆動のバックテスト(Cerebro・broker の成行/指値/逆指値)",
    3: "先物の系統的な売買の枠組み(予測値 → 建玉 → 口座の曲線)", 4: "足の上の戦略の枠組み(成行・指値、buy/sell_delay)",
    5: "調査報告の 5 番の行の実体は PyPI の bt(価格の表の上のアルゴの木)", 6: "zipline の分岐(polars のデータ源、成行・指値・逆指値)",
    7: "Node.js の取引の場。低頻度の売買の模擬は注文の率の式・成行/指値・段の中の逆指値/利確の判定",
    8: "TypeScript の bot の枠組み。バックテストは足ごとに注文を置き、成行は次の足の終値",
    10: "規則の表(enter / exit)を OHLCV の表全体に当てるバックテスト(残高の全部で売買)",
    11: "暗号資産の bot(OctoBot)。模擬は足から作った約定(次の足の安値・高値)で注文を当てる",
    12: "取引所の HTTP / WebSocket の接続と DataStore", 13: "Node.js の暗号資産の bot。模擬は約定の列の上の指値",
    15: "Rust の作業空間。CandleSimulator は合図の次の足の始値で約定、足の中の逆指値・利確",
    16: "yfinance の足の上の小さな事象駆動のバックテスト(次の行の始値で約定)",
    18: "株のイベント駆動のバックテスト(bundle の分足・日足、次の分の終値で約定)", 19: "暗号資産の枠組み(道具台帳 §3 の 11 件)",
    20: "CTA の足のバックテスト(vnpy_ctastrategy、次の足で約定)", 21: "ML の一気通貫の枠組み(Order は数量と方向と時間の窓)",
    23: "HFT の板と約定の事象の上の模擬(Rust の核)", 40: "チャートの上で検証する閉じた場(Market Intelligence Platform)",
    43: "AI の戦略の場(公開の repo にはバックテストの費用の既定値と経路だけ)", 44: "(道具台帳 §3 の 11 件)",
    45: "閉じた有料の練習の場(ForexTester)", 46: "MT4 の上の有料の練習の道具", 48: "登録の要る閉じた練習の場(BacktestingMax)",
    50: "閉じた有料の検証の場(AlgoTest)", 51: "(道具台帳 §3 の 11 件)", 52: "C# のアルゴリズム取引の機関(LEAN)。FillModel は足の終値・指値の厳密な通過",
    53: "中国株の事象駆動のバックテスト(日足では次の足への約定を捨てる)", 54: "価格の表と建玉の割合の表から収益率を出すバックテスト",
    55: "足の上の戦略の枠組み(次の足の始値で約定、合図は足 1 から)", 56: "中国株の量的取引の枠組み。模擬の口座は合図の足の終値で約定",
    57: "C++ の取引の核。CTA の模擬は足を開高安終の 4 つの tick にし、合図は次の tick(次の足の始値)で約定",
    58: "(道具台帳 §3 の 11 件)", 60: "C++ の核の中国株の取引の系(System)。既定で合図は次の足の始値へ遅らせる",
    61: "Rust の取引の枠組み。模擬の取引所は成行だけで、注文に書いた値で約定", 62: "イベント駆動のバックテスト(分足では次の分の足の始値で約定、逆指値あり、指値なし)",
    67: "Python の取引の枠組み。バックテストの broker は次の足の始値・指値・逆指値の値", 68: "イベント駆動のバックテスト(成行はその足の終値で即時)",
    69: "Go のイベント駆動のバックテスト(成行だけ、最新の足の終値で約定)", 70: "Pine の核を C で持つ枠組み(C API で成行・指値・逆指値)",
    72: "暗号資産の戦略の枠組み(tune と指標の表)", 73: "ベクトル化のバックテスト(from_signals / from_orders)",
    74: "(道具台帳 §3 の 11 件)", 75: "足の戦略の bot とバックテスト(取引所の市場の情報が要る)",
    80: "取引の bot。strategy_v2 のバックテストは executor を終値の表の上で模擬(三重の障壁)",
    85: "チャンの理論の信号(Rust の拡張)。検証の本体は wbt(候補 120)", 86: "記事に付いた backtrader の戦略の写経の集まり",
    87: "先物のトレンドフォローの枠組み(建玉の系列と価格の系列から収益)", 92: "予測市場のバックテスト(値は確率 [0, 1])",
    93: "予測市場の二値の市場の一気通貫の系(合成の市場か取得の市場)", 94: "Python 2 の小さなバックテスト(指値・逆指値・成行、足の値幅で約定)",
    107: "日足の価格の表の上の信号の言語(重み → 終値から終値の収益)", 111: "(道具台帳 §3 の 11 件)", 120: "(道具台帳 §3 の 11 件)",
    121: "株と ETF の日足のバックテスト(AlphaModel の目標の重み)", 122: "事象駆動のバックテスト(成行は次の足の始値)",
    123: "zenbot の本家(13 と同じ commit 52872fb4 の engine)",
}

DANGER = {19, 44, 51, 58, 74, 111, 120}
SCANLINE = {7: 6855, 13: 6874, 19: 9403, 40: 5725, 43: 4626, 44: 5904, 45: 10082, 46: 5727, 48: 5729, 50: 10088, 51: 9404,
            58: 6345, 74: 5910, 85: 5744, 86: 5746, 93: 4681, 107: 6917, 111: 10102, 120: 5918, 123: 7298}
ZB = "https://github.com/DeviaVir/zenbot/blob/52872fb4b5f9d10e2f891d95daec05da0b721ceb/lib/engine.js"
SIGC = "https://github.com/Skelf-Research/sigc/blob/aa5f616fc0faffafc072e71f39a26604aaae1474/crates/sig_runtime/src"
QD = "https://github.com/OpenByteInc/QuantDinger/tree/7da255c1e754daf939e1c58066ca2e44eb701b43/backend_api_python"
CZSC = "https://github.com/waditu/czsc/blob/701e480a545004f945bb1721e510ae610ad90c4c/czsc/traders/__init__.py"
BME = "https://github.com/punyamodi/binary_market_engine/blob/da3a599422aeca3af677ccd816882a542633df26"
OTR = "https://github.com/Open-Trader/opentrader/blob/8b8e24599599df214b12b4263553885854015b4b/packages/backtesting/src/backtesting-report.ts"


def _scan_lines():
    out = {}
    with open(HERE.parents[3] / "docs" / "DATA" / "tools_catalog.tsv", encoding="utf-8") as f:
        for i, row in enumerate(csv.reader(f, delimiter="\t")):
            if i and row and row[0].isdigit() and len(row) > 16:
                out[int(row[0])] = row[16]
    return out


CATLINE = _scan_lines()


def not_run(n: int, v: str):
    """(implementation column, judgement, reason) for a candidate neither run nor reproduced."""
    if n in DANGER:
        extra = ""
        if n == 120:
            extra = " 候補 85 czsc の検証の本体(czsc/traders/__init__.py 27 行 `from wbt import WeightBacktest`)。"
        return (f"(a) の書き写しだけ(SCAN {SCANLINE[n]} 行。道具台帳 §3 の 11 件なので導入も一次資料の読みもしない)", "再現できない",
                f"危険(道具台帳 §3 の 11 件 = 委任文 §4。導入も一次資料の読みもしない)。(a) の書き写し(SCAN {SCANLINE[n]} 行)は"
                f"機能の説明までで、この観点の規則を書き写せる行が無い。(b) は危険のため読まない。{extra}")
    if n in (13, 123):
        return (f"実装のコードで確かめた(一次資料 {ZB} を読むだけの複製 <b_reads>/DeviaVir_zenbot・carlos8f_zenbot、同じ commit)",
                "持たないと確認した",
                f"足(OHLC)を受ける口が無い: 入力は約定の列(engine.js 23-24 行 eventBus の 'trade' / 'trades')で、足は engine 自身が約定から作る"
                f"(135-167 行: s.period の open / high / low / close は trade.price)。場面の足を約定の列に作り直すのは adapter の計算になる({ZB})")
    if n in (40, 45, 46, 48, 50):
        return (f"(a) の書き写し(SCAN {SCANLINE[n]} 行)と (b) の公開の頁だけ(コードは公開されていない)", "再現できない",
                f"(a) SCAN {SCANLINE[n]} 行は場の機能の文言だけで、約定・費用・指標の式が無い。(b) 一次資料は閉じた場(登録・購入が要る)で、"
                "実装のコードが公開されていない。登録・購入はしない(委任文 §4)")
    if n == 43:
        return (f"実装のコードで確かめた(一次資料 {QD} の公開の複製 <read>/OpenByteInc_QuantDinger)", "再現できない",
                f"(a) SCAN {SCANLINE[n]} 行は場の説明だけ。(b) 公開の repo(975 ファイル)にあるのはバックテストの費用の既定値"
                "(app/services/backtest_execution.py 19-28 行: 手数料・滑り 0.0005)・期間の上限・経路・試験だけで、足の約定の本体"
                "(scripts/stress_backtest_engine_v2.py 12 行が読む tests.helpers.backtest_stress_cases も)がファイルの一覧に無い")
    if n == 85:
        return (f"実装のコードで確かめた(一次資料 {CZSC} を読むだけの複製 <read>/waditu_czsc)", "再現できない",
                f"危険: 検証の本体は wbt(候補 120 = 道具台帳 §3 の 11 件)で、czsc/traders/__init__.py 27 行が `from wbt import WeightBacktest`"
                f"({CZSC})。(a) SCAN {SCANLINE[n]} 行は「検証の本体は別の配布物 wbt、信号の核は Rust の拡張」まで。(b) wbt は危険のため読まない")
    if n == 86:
        return ("(a) の書き写し(SCAN 5711・5746 行)", "スキップ: 明らかに弱い",
                "上位互換: 候補 86 は道具ではなく記事に付いた backtrader の戦略の写経の集まり(SCAN 5711 行「道具ではなく、記事に付いた写経の集まり」、"
                "`2019-09-26-backtrader-backtesting-trading-strategies/`)で、足の約定の機構は backtrader(候補 2)そのもの。候補 2 はこの観点の場面に"
                "通した(survey_results/opp_backtrader.tsv)")
    if n == 107:
        why = {"I4-17": f"12 の指標の口が無い: 指標は重みの収益の系列から(backtest.rs calculate_metrics 42 行)で、決済ごとの損益が無い。metrics.rs は処理の計測(11-117 行)",
               "I4-18": f"行の割合で 3 つに分ける口が無い: walk_forward.rs 9-56 行は学習と検証の期間の本数(train_periods / test_periods)で転がす 2 分割"}
        base = (f"注文・約定・始値の口が無い: backtest.rs 23-52 行は重みの表と価格の表から終値から終値の収益(63-71 行)と重み x 収益(98-140 行、"
                f"1 足の遅れ)を出すだけで、注文(種類・値・数量)・約定の記録・足の始値・高値・安値を使う行が無い({SIGC}/backtest.rs)")
        return (f"実装のコードで確かめた(一次資料 {SIGC} を読むだけの複製 <read>/Skelf-Research_sigc。項目 0 が構築した実行ファイルは消えている)",
                "持たないと確認した", why.get(v, base))
    if n == 93:
        return (f"実装のコードで確かめた(一次資料 {BME} を読むだけの複製 <read>/punyamodi_binary_market_engine)", "持たないと確認した",
                f"宣言でファイル(約定・気配・足)を読む口が無い: 市場は合成(fetch_data.py 151 行 generate_synthetic_markets、main.py 111-114 行 "
                f"use_mock=not args.live)か取得(fetch_data.py 40-150 行 Polymarket / Kalshi の API)で、値の動きは種つきの乱数の模擬(simulator.py 9-42 行)。"
                f"書き出しは JSON 1 本(main.py 124-144 行)で、目的の札・ダッシュボードの口が無い({BME})")
    raise KeyError(n)


def rows_of(target):
    p = RES / f"{target}.tsv"
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def clean(detail: str) -> str:
    d = detail.replace("|", "/").replace("\n", " ")
    if d.startswith("場合 "):
        d = d.split(": ", 1)[1] if ": " in d else d
    if d.startswith("adapter: "):
        d = d[len("adapter: "):]
        if ": " in d:
            d = d.split(": ", 1)[1]
    return d.strip()


def reasons(rows):
    seen, out = set(), []
    for r in rows:
        for part in clean(r["detail_1"]).split(" / "):
            part = part.strip()
            if part and part not in seen:
                seen.add(part)
                out.append(part)
    s = " / ".join(out)
    return s if len(s) <= 900 else s[:900] + "…"


# a statement of not having read / not having checked, matched with anything in between (「読んだ範囲(a.py・b.py)に無い」
# is the same statement as 「読んだ範囲に無い」; i4-r2-04: a substring match missed the parenthesised form)
UNVERIFIED = re.compile(r"読んだ範囲.*?に無い|読んでいない|確かめていない|未確認|再現していない")
# the answer of an adapter / reproduction that is not about the tool at all (the scene set's own barriers, i4-r1-05)
BARRIER_WORDS = ("足 0 の合図", "maker と taker で違う手数料")
# a part that is the adapter's own choice, not the tool's absence (the tool may have the mouth)
ADAPTER_WORDS = ("この adapter", "写していない", "書いていない")


def split_reason(detail: str) -> list:
    """The parts of one scene's reason (an adapter / reproduction joins them with ' / ')."""
    return [x.strip() for x in clean(detail).split(" / ") if x.strip()]


def verified_absence(part: str, need_line: bool = True) -> bool:
    """A part that says a mouth is missing and shows it, with no word of not having read it and not one of the scene
    set's own barriers (規則 6).  A tool run in its venv shows it by the call itself (the runner's command and its
    output = the adapter's answer after calling the tool): need_line=False.  A reproduction shows it by a line of the
    primary source: need_line=True (a code line or a URL)."""
    if UNVERIFIED.search(part) or any(w in part for w in BARRIER_WORDS + ADAPTER_WORDS):
        return False
    if not ("無い" in part or "無く" in part or "だけ" in part):
        return False
    return (not need_line) or ("行" in part or "http" in part or ".py" in part or ".rs" in part or ".js" in part
                               or ".ts" in part or ".cs" in part or ".cpp" in part or ".go" in part)


def barrier_free(scene_id: str) -> bool:
    return not S.barriers(S.by_id(scene_id))


def judge_row(rows, need_line: bool = True):
    """(judgement, parts) of a candidate whose every scene of the viewpoint ended in 「結果なし」:
    「持たないと確認した」 only when every barrier-free value scene of the viewpoint (every scene when it has none)
    failed with at least one verified absence -- parts = those verified absences (the reason shows only them);
    otherwise 「再現できない」 -- parts = the reasons of the scenes without one (what was not read, i4-r1-08)."""
    val = [r for r in rows if r["kind"] == "値" and barrier_free(r["scene"])] or rows
    unverified, verified = [], []
    for r in val:
        parts = split_reason(r["detail_1"])
        ok = [x for x in parts if verified_absence(x, need_line)]
        if ok:
            verified += [x for x in ok if x not in verified]
        else:
            unverified += [x for x in parts if x not in unverified]
    return ("持たないと確認した", verified) if not unverified else ("再現できない", unverified)


def joined(parts, limit=900):
    s = " / ".join(parts)
    return s if len(s) <= limit else s[:limit] + "…"


def target_of(n):
    for t, spec in T.TARGETS.items():
        if spec.get("cand") == n:
            return t, spec
    return None, None


def summary(rows):
    c = {}
    for r in rows:
        c[r["class_1"]] = c.get(r["class_1"], 0) + 1
    return "・".join(f"{k} {v}" for k, v in sorted(c.items()))


def main():
    vps = list(S.VIEWPOINTS)
    out = ["# 項目 4「統合と答え合わせ」— 動かせなかった候補の検討表", "",
           "場面係が書く(委任文 §3「動かせない候補の検討と再現」・場面集の規則 6・9)。この表は `tests/bt/battery/item_4/gen_considered.py` が作る。", "",
           "- 候補 = REQUIREMENTS.md §3 が機械で抜き出したものだけ(人が足し引きしない): I4-1〜I4-4 は 0 件(§3.1)、I4-5 は 121・21・93・hftbacktest、"
           "I4-6 は 75・19・8・12(§3.2)、I4-8〜I4-18 は台帳の 足 = ○ の 55 件(§3.3)、I4-7・I4-19・I4-20 は SCAN の対象外(§3.4)。"
           "**§3.2 が「候補 1 `hftbacktest`」と書く 1 は SCAN の節の中の通し番号で、台帳の番号は 23**(台帳の 1 は Basana)。ここでは 23 として扱う。"
           "**台帳の 11 の名の列は `python3` だが、SCAN 8452 行はこれを OctoBot と書く**(項目 0 も OctoBot として扱った)。",
           "- 「動かせた候補」= 隔離した venv で動き、その観点の場面で「結果なし」以外(正解と一致・不一致・対応なし)を 1 つ以上返した候補"
           "(survey_results/opp_*.tsv から機械で数えた)。導入はできたがその観点の場面を 1 つも取れなかった候補は、その観点では表の行に載せる。",
           "- 段: この項目のどの観点にも無い(REQUIREMENTS.md §3.0・§3.3)。だから「段が低い」を理由にしたスキップは無い。上位互換のスキップは 86 だけ"
           "(機構が候補 2 そのもの)。",
           "- 「再現した」の候補は、一次資料を読むだけで(実行しない)場面に掛かる規則を opponents/repro_*.py に行を 1 対 1 で書き写し、場面集の全部の"
           "場面に通した(survey_results/opp_repro_*.tsv)。共通の部分(注文の並び・建玉・場面の戦略)は opponents/_repro_bars.py で、道具ごとに違う規則は"
           "全部 repro の側に置いた。",
           "- 実装の列の <venvs> は `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs`、<read> は同じ scratchpad の"
           "`bt/i4_r1_scenekeeper/read`(読むだけの複製と取得の記録 i4_r1_scenekeeper_read.log)、<b_reads> は `bt/b_reads`(前の項目の読むだけの複製)。",
           "- 導入・構築の試みの全部(動かせた候補を含む)は opponents/RUNNABILITY.tsv。", ""]
    run_rows = []
    all_cands = sorted({n for p in POOL.values() for n in p})
    for v in vps:
        title = f"### 観点 {v} {S.VIEWPOINTS[v]}"
        out += [title, ""]
        pool = POOL.get(v)
        if not pool:
            out += ["動かせた候補: 0 件", "", f"候補 0 件: {ZERO[v]}", ""]
            if v in ("I4-1", "I4-2", "I4-3", "I4-4"):
                out += ["(この観点の候補は 0 件。I4-8〜I4-18 の候補で動いたもの・再現したものは、この観点の場面にも通した: survey_results/opp_*.tsv)", ""]
            continue
        runnable, table = [], []
        for n in pool:
            t, spec = target_of(n)
            name = NAMES[n]
            if t is None:
                impl, j, why = not_run(n, v)
                table.append((n, name, MECH.get(n, ""), impl, j, why))
                continue
            rows = [r for r in rows_of(t) if r["viewpoint"] == v]
            got = [r for r in rows if r["class_1"] != "結果なし"]
            if n == 70 and not got:
                table.append((n, name, MECH.get(n, ""), f"実装を呼んだ(項目 2 の構築物 <venvs>/item_2/drivers/i2drv70。対象 {t})", "再現できない",
                              "(a) SCAN の書き写しは機構の説明まで(C API の成行・指値・逆指値の型の名)。(b) 一次資料の複製(<venvs>/item_2/src/c70、"
                              "commit 5e62602c)と構築物・C の driver の source は、この役の最初の走行のあと他の役の容量の片付けで消えた"
                              '(この役は消していない)。第 r3-1 回に構築し直しを試みた: 最初の clone は 5e62602c ではない版 0d76a099 を返し、場面係は導入前の検査をせずに CMake で構築した(§4 から外れた。その clone と構築物はリードの指示で消した。<venvs>/item_2/logs/i4_r3-1_scenekeeper_rebuild_70.log・i4_r3-1_scenekeeper_refetch_70.log)。検査した版 5e62602c を git fetch で取り直した(構築していない)が、前の検査の記録を当てて構築・実行へ進む操作を、この環境の許可の判定が [Code from External] として止めた。容量では止めていない(df -m / の空き 2,046 MB → 1,943 MB)。**比べていない**(理由: 道具を 1 度も呼べていない。survey_results/opp_pineforge.tsv の理由)'))
                continue
            if spec.get("venv"):
                if got:
                    runnable.append(f"{n} {name}")
                    continue
                impl = f"実装を呼んだ(対象 {t}、<venvs>/{spec['venv']})"
                j, unv = judge_row(rows, need_line=False)
                if j == "持たないと確認した":
                    why = (f"場面が測る能力の口が無い: `python3 tests/bt/battery/item_4/run_battery.py --target {t} --out …` の出力 "
                           f"survey_results/{t}.tsv の {v} の行が全部「結果なし」。本題でない物の無い値の場面のそれぞれに、行を引いた「無い」がある"
                           f"(道具を実際に呼んだ adapter の理由のうち、その部分): {joined(unv)}")
                else:
                    why = (f"(a) SCAN の書き写し(SCAN {CATLINE.get(n, '?')} 行)は機構の説明まで。(b) 道具を実際に呼んだ adapter の理由に、"
                           f"行を引いた「無い」の無い場面がある(確かめていない部分: {' / '.join(unv)[:500]})。出力 survey_results/{t}.tsv")
                table.append((n, name, MECH.get(n, ""), impl, j, why))
                continue
            mod = spec["module"]
            impl = f"実装のコードで確かめた(一次資料を読むだけで書き写した {mod}。出典の URL と行は同じファイルの冒頭)"
            if got:
                table.append((n, name, MECH.get(n, ""), impl, "再現した",
                              f"一次資料の規則を {mod.replace('opponents/', 'opponents/')} に書き写し、場面に通した: survey_results/{t}.tsv の {v} の行 = {summary(rows)}"))
                continue
            rs = reasons(rows)
            if n == 8 and v == "I4-6":
                table.append((n, name, MECH.get(n, ""), f"実装のコードで確かめた(一次資料 {OTR} を読むだけの複製 <b_reads>/Open-Trader_opentrader)",
                              "持たないと確認した",
                              f"目的の札(動作確認 / 研究)を書き出しに付ける口・固定の手順の口が無い: バックテストの報告は注文の表と合計の損益"
                              f"(backtesting-report.ts 24-75 行、{OTR})。紙の売買(Paper Trading, SCAN 3823 行)は実行の型の切替で、札を強制しない"))
                continue

            j, unv = judge_row(rows)
            if j == "再現できない":
                table.append((n, name, MECH.get(n, ""), impl, "再現できない",
                              f"(a) SCAN の書き写し(SCAN {CATLINE.get(n, '?')} 行)は機構の説明までで、この観点の規則を書き写せる行が無い。(b) 一次資料のうち"
                              f"読んだ範囲では、この観点の場面に要る部分を確かめていない(確かめていない部分: {' / '.join(unv)[:500]})。"
                              f"理由の全部: {rs}(出力 survey_results/{t}.tsv、{mod})"))
            else:
                table.append((n, name, MECH.get(n, ""), impl, "持たないと確認した",
                              f"一次資料の行で確かめた: 書き写し {mod} を場面に通した出力 survey_results/{t}.tsv の {v} の行が全部「結果なし」。"
                              f"本題でない物の無い値の場面のそれぞれに、行を引いた「無い」がある(その部分): {joined(unv)}"))
        out += [f"動かせた候補: {len(runnable)} 件" + (f"({', '.join(runnable)})" if runnable else ""), ""]
        if table:
            out += ["| 候補 | 機構 | 実装 | 判断 | 理由 |", "|---|---|---|---|---|"]
            for n, name, mech, impl, j, why in table:
                out.append(f"| {n} {name} | {mech} | {impl} | {j} | {why} |")
            out.append("")
        else:
            out += [f"動かせなかった候補 0 件: `REQUIREMENTS.md §3 の {v} の候補は全部動かせた`", ""]
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    write_runnability(all_cands)
    print(OUT)


RUN_NOTES = {
    2: "PyPI の backtrader(項目 0 の venv item_0/backtrader)", 55: "PyPI の backtesting(項目 0 の venv item_0/backtesting)",
    73: "PyPI の vectorbt(項目 1 の venv item_1/vectorbt)", 122: "PyPI の PyAlgoTrade 0.20(この役の venv item_4/pyalgotrade、記録 venvs/item_4/i4_r1_scenekeeper_install_pyalgotrade.log)",
    4: "PyPI の lib-pybroker(この役の venv item_4/pybroker、記録 i4_r1_scenekeeper_install_pybroker.log)",
    16: "git clone 20929924(項目 3 の venv item_3/c16。clone が他の役の片付けで消えていたので同じ commit を同じ場所に clone し直した: venvs/item_4/i4_r1_scenekeeper_reclone_c16.log)",
    20: "PyPI の vnpy と vnpy_ctastrategy(項目 0 の venv item_0/vnpy)", 1: "PyPI の basana(項目 0 の venv item_0/basana)",
    5: "PyPI の bt(項目 2 の venv item_2/bt。調査報告の 5 番の行の実体)", 72: "PyPI の qtradex(項目 2 の venv item_2/qtradex)",
    6: "PyPI の ziplime(項目 2 の venv item_2/ziplime)", 121: "PyPI の qstrader(項目 0 の venv item_0/qstrader)",
    54: "PyPI の finmarketpy(項目 1 の venv item_1/finmarketpy。plotly 7 で import が落ちたので plotly<6 をこの venv に足した: venvs/item_4/i4_r1_scenekeeper_install_finmarketpy_fix.log)",
    3: "git の 8958c49c(項目 1 の venv item_1/c3。clone が消えていたので同じ commit を取り直し、data/ と .git を消した: venvs/item_4/i4_r1_scenekeeper_reclone_c3_c87.log)",
    21: "PyPI の pyqlib(項目 1 の venv item_1/qlib)", 23: "PyPI の hftbacktest(項目 1 の venv item_1/hftbacktest)",
    87: "git の 439232ae(項目 1 の venv item_1/c87。clone を取り直した: 同じ記録)", 12: "PyPI の pybotters(項目 0 の venv item_0/pybotters)",
    75: "PyPI の freqtrade(項目 3 の venv item_3/freqtrade)", 92: "git clone(項目 2 の venv item_2/c92)",
    53: "PyPI の rqalpha(この役の venv item_4/rqalpha、記録 i4_r1_scenekeeper_install_rqalpha.log)",
    70: '項目 2 が CMake で構築し C の driver で走らせた(item_2/src/c70・drivers/i2drv70)。この役の最初の走行では走ったが、その後 clone・構築物・driver の source が他の役の片付けで消えた。第 r3-1 回: 最初の clone は版 0d76a099(5e62602c ではない)で、導入前の検査をせずに CMake で構築した(§4 から外れた。リードの指示で消した。記録 item_2/logs/i4_r3-1_scenekeeper_rebuild_70.log)。検査した版 5e62602c を git fetch で取り直した(記録 item_2/logs/i4_r3-1_scenekeeper_refetch_70.log、構築していない)が、構築・実行へ進む操作をこの環境の許可の判定が [Code from External] として止めた。容量では止めていない(空き 2,046 MB → 1,943 MB)。比べていない(道具を呼べていない)',
    68: "PyPI の quanttrader 0.5.5(この役の venv item_4/quanttrader。np.str / DataFrame.append のため numpy 1.23.5・pandas 1.5.3・matplotlib 3.7.5 をこの venv に固定: 記録 i4_r1_scenekeeper_install_quanttrader.log)",
    10: "PyPI の fast-trade 2.1.0(この役の venv item_4/fast-trade)", 62: "PyPI の qf-lib 4.0.7(この役の venv item_4/qf-lib。宣言されていない PyJWT・oauthlib・requests-oauthlib を足した: 記録 i4_r1_scenekeeper_install_qf-lib.log)",
    18: "PyPI の zipline-reloaded 3.1.1(この役の venv item_4/zipline-reloaded、記録 i4_r1_scenekeeper_install_zipline-reloaded.log)",
}
MEASURED = ("導入を試みた(第 r2-1 回): 隔離した venv で `pip install --dry-run --ignore-installed --report` が {n} 件のファイルに解決"
            "(opponents/attempts/i4_r2-1_scenekeeper_dryrun_{pkg}.log)、解決した全ファイルの大きさを PyPI の公開の情報から足すと {mib} MiB"
            "(opponents/attempts/i4_r2-1_scenekeeper_install_size_measure.txt、i4_r2-1_scenekeeper_sizes.py)。そのときの空き容量は 826,646,528 バイト"
            "(df -B1 /、2026-09-26T08:44Z。この環境の容量が 19 MB まで落ちた実測が第 17 周にある)で、展開後は取得の大きさより大きいので、"
            "並行する役の作業を止めないように導入を止めた(容量の実測で止めた)。一次資料から再現した")
NOT_INSTALLED = {
    67: MEASURED.format(pkg="lumibot", n=320, mib="572.3"), 60: MEASURED.format(pkg="hikyuu", n=104, mib="470.5"),
    15: "Rust の作業空間で crate の取得に資格情報が要る(項目 3 の記録)。一次資料から再現した", 8: "導入前の検査(調査の委任文 §6-1)で止めた(項目 3 の記録)。一次資料から再現した",
    56: MEASURED.format(pkg="zvt", n=57, mib="121.4") + "。足は道具自身のデータベースから読む(get_kdata)",
    69: "項目 0 の Go の driver(item_0/c69)が消えている。一次資料から再現した", 11: "検証に触手(tentacles)が要り、既定の触手は PyPI の外の zip(項目 0 の記録)。一次資料から再現した",
    7: "Node.js の場(データの採掘と UI を含む)。導入していない。一次資料から再現した", 52: "C# / .NET(項目 0 の記録)。一次資料から再現した",
    57: "C++ の構築(項目 0 の記録)。一次資料から再現した", 94: "Python 2 の文法(この環境に Python 2 は無い)。一次資料から再現した",
    80: "pip の構築が失敗(opponents/attempts/i4_r1_scenekeeper_dryrun_resolution.log)。一次資料から再現した",
    61: "項目 0 の cargo の driver(item_0/c61)が消えている。構築し直しは容量(空き 2.3 GB、項目 0 の 107 の構築だけで 2.0 GB)で試していない。一次資料から再現した",
    13: "Node.js の bot。入力が約定の列で足を受けないので導入していない", 123: "13 と同じ engine(同じ commit)", 107: "項目 0 が cargo で構築した実行ファイルが消えている。重みの言語で注文の口が無いので構築し直していない",
    85: "pip install --dry-run: 38 件の依存に wbt==0.9.1(候補 120、道具台帳 §3 の 11 件)が入るので導入しない", 86: "記事の写経の集まり(道具ではない)",
    93: "導入していない(一次資料を読んだ)", 43: "公開の repo に足の約定の本体が無い", 40: "閉じた場(登録しない)", 45: "閉じた有料の場", 46: "有料の MT4 の道具(購入しない)",
    48: "閉じた場(登録しない)", 50: "閉じた有料の場",
}


def write_runnability(cands):
    rows = [["cand", "name", "tried", "result", "target", "reason"]]
    for n in cands:
        t, spec = target_of(n)
        name = NAMES[n]
        if n in DANGER:
            rows.append([n, name, "導入も実行もしない(道具台帳 §3 の 11 件 = 委任文 §4)", "走らなかった", "-", "危険"])
        elif t and spec.get("venv"):
            res = rows_of(t)
            ok = any(r["class_1"] != "結果なし" for r in res)
            loaded = not any(r["detail_1"].startswith("対象を読み込めない") for r in res)
            rows.append([n, name, RUN_NOTES.get(n, spec["venv"]), "走った" if loaded and n != 70 else "走らなかった(最後の走行)",
                         t, "-" if ok else "場面を 1 つも取れなかった(理由は survey_results の行)"])
        elif t:
            rows.append([n, name, NOT_INSTALLED.get(n, "-"), "再現した", t, "-"])
        else:
            rows.append([n, name, NOT_INSTALLED.get(n, "-"), "走らなかった", "-", "検討表の行"])
    with open(RUNTSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerows(rows)


if __name__ == "__main__":
    main()
