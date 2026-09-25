"""Item 2 battery: writes opponents/RUNNABILITY.tsv (one install record per candidate of pool.tsv) and
opponents/CONSIDERED.md (the review table of the candidates that could not be run, per viewpoint).

Mechanical parts (no hand counting):
- the candidates per viewpoint = pool.tsv (gen_pool.py, REQUIREMENTS.md §3);
- 段(機構) / 段(既定) / 遅延 / 取り消しの扱い and the survey-report rows = docs/DATA/tools_catalog.tsv;
- "動かせた候補" of a viewpoint = a candidate with a real-tool target whose survey_results/<target>.tsv has at least one
  scene of that viewpoint with a result other than 結果なし; a candidate whose targets ran but gave 結果なし for every
  scene of the viewpoint gets a table row built from the adapter's own refusal (the command and its output);
- a reproduction target (opponents/repro_*.py) makes its candidate's row 再現した wherever it returned a result.
Hand-written parts: FACTS below (the not-run candidates' mechanism, where it was read, the verdict and its reason; every
reason names the survey-report line or the primary-source file it rests on).  Run, then
`python3 scripts/check_bt_considered.py tests/bt/battery/item_2/opponents/CONSIDERED.md --write`.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))

import i2_targets as T  # noqa: E402

VPS = ["C2-1", "C2-2", "C2-3", "C2-4", "C2-5", "C2-6", "C2-7", "C2-8", "C2-9", "C2-10", "C2-11", "C2-12"]
VP_NAME = {"C2-1": "発注の型", "C2-2": "取消と訂正", "C2-3": "取引所の規則", "C2-4": "異常系(拒否・時間切れ・状態不明・停止)",
           "C2-5": "約定/待ち行列の段", "C2-6": "先行注文の取消の扱い", "C2-7": "市場影響", "C2-8": "楽観側・悲観側の幅",
           "C2-9": "遅延", "C2-10": "費用", "C2-11": "口座と会計", "C2-12": "JPX のデータ待ち"}
TIERED = {"C2-5", "C2-7"}
ZERO = {"C2-4": "grep -inE 'self[- ]?trade|self_match|STATE_UNKNOWN|kill.switch|呼値|tick size' SCAN_clean.md(REQUIREMENTS.md §3.2)",
        "C2-8": "REQUIREMENTS.md §3.1 の C2-8(tools_catalog.tsv にこの軸の列が無く、SCAN への grep の候補 0)",
        "C2-12": "awk -F'\\t' '$1==\"C2-12\"' tests/bt/battery/item_2/pool.tsv(REQUIREMENTS.md §3 に C2-12 の候補の抜き出しが無い)"}
# the catalogue's name vs the survey report's line for the same number (reported to the lead in the page header)
NAME_FIX = {5: "bt・台帳の名は Lean CLI", 11: "OctoBot・台帳の名は python3"}
VENVS = "/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs"


def catalog():
    out = {}
    with open(REPO / "docs/DATA/tools_catalog.tsv", encoding="utf-8") as fh:
        r = csv.reader(fh, delimiter="\t")
        next(r)
        for row in r:
            row += [""] * (20 - len(row))
            out[int(row[0])] = {"name": row[1], "mech": row[9], "dflt": row[10], "lat": row[11], "cxl": row[12],
                                "row": row[16], "trow": row[17], "lat_raw": row[18], "cxl_raw": row[19]}
    return out


def pool():
    out = {v: [] for v in VPS}
    names = {}
    with open(HERE / "pool.tsv", encoding="utf-8") as fh:
        r = csv.reader(fh, delimiter="\t")
        next(r)
        for v, c, n, *_ in r:
            if int(c) not in out[v]:
                out[v].append(int(c))
            names[int(c)] = NAME_FIX.get(int(c), n)
    return out, names


def results():
    """target -> {viewpoint: [(scene, class, detail)]}"""
    out = {}
    for f in sorted((HERE / "survey_results").glob("*.tsv")):
        rows = {}
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                rows.setdefault(r["viewpoint"], []).append((r["scene"], r["class_1"], r["detail_1"]))
        out[f.stem] = rows
    return out


def targets_by_cand():
    allt = {**T.TARGETS, **getattr(T, "SURVEY", {})}
    real, repro = {}, {}
    for k, t in allt.items():
        if isinstance(t, dict) and t.get("cand") is not None:
            (repro if "repro_" in t["module"] else real).setdefault(t["cand"], []).append(k)
    return real, repro


# ------------------------------------------------------------------ install records (one per candidate)
I0 = "tests/bt/battery/item_0/opponents/RUNNABILITY.tsv"
L2 = "scratchpad bt/venvs/item_2/logs"
RUN = {
    1: ("PyPI の basana を項目0 が入れた venv item_0/basana で走らせた", "走った", ""),
    2: ("PyPI の backtrader を項目0 が入れた venv item_0/backtrader で走らせた", "走った", ""),
    3: ("項目0 の venv item_0/c3(git clone を .pth)で走らせた。17:06Z の実行のあと、この venv は他の役に消された(この役は消していない)", "走った", ""),
    4: ("項目0 の venv item_0/lib-pybroker で走らせた。17:17Z の実行のあと、この venv は他の役に消された", "走った", ""),
    5: (f"PyPI の bt 1.2.3(SCAN 6849 行の名は bt。台帳の名 Lean CLI は SCAN の行と合わない)を隔離した venv item_2/bt に入れた({L2}/i2_r1_scenekeeper_install_5.log)", "走った", ""),
    6: (f"PyPI の ziplime 1.19.16(項目0 が検査した版)を venv item_2/ziplime に入れ直した({L2}/i2_r1_scenekeeper_install_6.log)。1 秒の足は 240 秒で終わらず打ち切った(同じ記録の試し)", "走った", ""),
    7: ("導入しない。Node.js の平台(SCAN 6855・6986 行)で、Python の venv に入れる配布物が無い", "走らなかった", "導入の形が違う"),
    8: ("導入しない(項目0 の記録を使う)", "走らなかった", f"危険(§6-1): {I0} の候補 8 の行(postinstall が prisma の生成・移行・種入れを走らせる、SCAN 3809 行)"),
    10: ("項目0 の venv item_0/fast-trade-r17 で走らせた。17:04Z の実行のあと、この venv は他の役に消された", "走った", ""),
    11: ("導入しない(項目0 の記録を使う)", "走らなかった", f"動かなかった: {I0} の候補 11 の行(検証は触手を要し、既定の触手は PyPI の外の zip で導入前の検査を通せない)"),
    12: ("PyPI の pybotters を項目0 が入れた venv item_0/pybotters で走らせた", "走った", ""),
    13: ("導入しない(項目0 の記録を使う)", "走らなかった", f"危険(§6-1): {I0} の候補 13 の行(postinstall が webpack と追加の外部取得を走らせる、SCAN 2966 行)"),
    15: ("導入しない(項目0 の記録を使う)。一次資料は読むだけの clone(read/c15)", "走らなかった", f"鍵・登録: {I0} の候補 15 の行(workspace の依存 ultra-logger が資格情報を要する)"),
    16: ("項目0 の venv item_0/luczinsritter で走らせた。17:16Z の実行のあと、この venv は他の役に消された", "走った", ""),
    18: ("項目0 の venv item_0/zipline-reloaded で走らせた。17:13Z の実行のあと、この venv は他の役に消された", "走った", ""),
    19: ("導入も実行も (b) もしない", "走らなかった", "危険: 道具台帳 §3 の 11 件"),
    20: ("PyPI の vnpy を項目0 が入れた venv item_0/vnpy で走らせた(足とティックの 2 つの型)", "走った", ""),
    21: ("項目1 が入れた venv item_1/qlib で走らせた", "走った", ""),
    23: ("項目1 が入れ直した venv item_1/hftbacktest(hftbacktest 2.4.4)で走らせた", "走った", ""),
    32: (f"git clone を venv item_2/c32 に .pth(依存なし)({L2}/c32.log)", "走った", ""),
    33: ("項目0 の構築(CMake のライブラリ)と項目2 の driver(drivers/i2drv33)で走らせた", "走った", ""),
    34: ("PyPI の QuantCore を項目0 が入れた venv item_0/quantcore で走らせた", "走った", ""),
    35: ("項目0 の venv item_0/c35_run/.venv で走らせた", "走った", ""),
    36: (f"git clone を読んだ(src/c36)。impactModel.py はモジュールの頭で Input/*.csv(実データ)を読み当てはめるだけの台本で、呼べる関数の口が無い(1-9・65-81 行)", "走らなかった", "呼ぶ口が無い(台本): 実データを読まずに呼べる関数が無い"),
    37: ("PyPI の trading_simulator を項目0 が入れた venv item_0/c37 で走らせた", "走った", ""),
    38: ("導入しない(項目0 の記録を使う)", "走らなかった", f"一括の取得(数百 MB 以上): {I0} の候補 38 の行(torch==2.6.0 ほか)"),
    40: ("導入しない(項目0 の記録を使う)", "走らなかった", f"外部の場: {I0} の候補 40 の行(導入する機関が無く、場に当方のデータを渡すことになる)"),
    41: ("導入も実行も (b) もしない", "走らなかった", "危険: 道具台帳 §3 の 11 件"),
    45: ("導入しない。検証はウェブの場(SCAN 10082 行)で、導入する配布物が無い", "走らなかった", "外部の場"),
    50: ("導入しない。検証はウェブの場(SCAN 10088 行)で、導入する配布物が無い", "走らなかった", "外部の場"),
    51: ("導入も実行も (b) もしない", "走らなかった", "危険: 道具台帳 §3 の 11 件"),
    53: ("PyPI の rqalpha を項目0 の venv item_0/rqalpha で走らせた。17:19Z の実行のあと、この venv は他の役に消された", "走った", ""),
    54: ("項目1 が入れ直した venv item_1/finmarketpy で走らせた", "走った", ""),
    57: ("導入しない(項目0 の記録を使う)。MatchEngine.cpp を一次資料から再現した(opponents/repro_57_wondertrader_match.py)", "走らなかった", f"導入前の検査を通せない・依存が repository の外: {I0} の候補 57 の行"),
    58: ("導入も実行も (b) もしない", "走らなかった", "危険: 道具台帳 §3 の 11 件"),
    60: (f"pip install --dry-run で依存を読んだ({L2}/i2_r1_scenekeeper_install_hikyuu.log: 104 件、PySide6 ほか)。入れていない", "走らなかった", "一括の取得(数百 MB 以上): PySide6 の画面の部品を含む 104 件"),
    61: ("項目0 が構築した driver(venv item_0/c61 の bin/c61_driver)で走らせた", "走った", ""),
    63: ("導入しない(項目0 の記録を使う)", "走らなかった", f"動かなかった: {I0} の候補 63 の行(CMake が Boost を見つけられず止まった)"),
    65: (f"項目0 の venv item_0/c65(依存と構築済みの binding)に、取り直した clone(src/c65、commit c4a07d41)を読ませた({L2}/i2_r1_scenekeeper_install_65.log)", "走った", ""),
    67: (f"pip install --dry-run で依存を読んだ({L2}/i2_r1_scenekeeper_install_lumibot.log: 320 件、google-adk・litellm・boto3 ほか)。入れていない", "走らなかった", "一括の取得(数百 MB 以上): 依存 320 件"),
    70: (f"clone(src/c70、commit 5e62602c)を道具の CMake で構築し、項目2 の C の driver(drivers/i2drv70)で走らせた({L2}/i2_r1_scenekeeper_install_70.log)", "走った", ""),
    72: (f"PyPI の QTradeX 1.8.0 を venv item_2/qtradex に入れた({L2}/i2_r1_scenekeeper_install_qtradex.log)", "走った", ""),
    73: ("項目1 が入れた venv item_1/vectorbt(vectorbt 1.1.0)で走らせた", "走った", ""),
    87: ("項目0 の venv item_0/c87 で走らせた。17:04Z の実行のあと、この venv は他の役に消された", "走った", ""),
    90: (f"git clone を venv item_2/c90 に .pth(依存なし)({L2}/c90.log)", "走った", ""),
    91: (f"git clone を取り直し(src/c91、commit 6cb8ea56)、venv item_2/c91 に httpx・pydantic・fastapi を入れた({L2}/i2_r1_scenekeeper_install_91.log)", "走った", ""),
    92: (f"git clone を venv item_2/c92 に .pth、pyproject の依存を PyPI から({L2}/c92.log)", "走った", ""),
    94: ("導入しない。backtest.py は Python 2 の文法(print 文、356 行)で、この環境に Python 2 は無い。一次資料から再現した(opponents/repro_94_mote_backtest.py)", "走らなかった", "動かなかった: Python 2 の台本"),
    95: (f"git clone を venv item_2/c95 に .pth(標準の部品だけ)({L2}/c95.log)", "走った", ""),
    96: ("clone の照合の部分を小さな C++ の driver(drivers/i2drv96)で構築して走らせた", "走った", ""),
    97: ("導入も実行も (b) もしない", "走らなかった", "危険: 道具台帳 §3 の 11 件"),
    98: (f"git clone を取り直し(src/c98、commit 6cc05366)、venv item_2/c98 に numpy を入れた({L2}/i2_r1_scenekeeper_install_98.log)", "走った", ""),
    99: (f"git clone を取り直し(src/c99、commit b767b0c4)、venv item_2/c99 に sortedcontainers を入れた({L2}/i2_r1_scenekeeper_install_99.log)", "走った", ""),
    100: ("導入しない(SCAN 10447 行: 公開された原典の照合の 4 関数の本体が空)", "走らなかった", "埋まりを決める本体が無い"),
    101: ("項目0 の記録どおり小さな C++ の driver(drivers/i2drv101)を構築して走らせた", "走った", ""),
    102: ("項目0 の venv item_0/c102(道具の CMake の Python の binding)で走らせた", "走った", ""),
    103: (f"git clone を取り直し(src/c103)、項目0 が入れた Python 3.14.7 の venv item_2/c103 に sortedcontainers・pydantic を入れた({L2}/i2_r1_scenekeeper_install_103.log)", "走った", ""),
    104: ("clone の照合の部分を小さな C++ の driver(drivers/i2drv104)で構築して走らせた", "走った", ""),
    105: ("項目0 の venv item_0/c105 で走らせた", "走った", ""),
    106: ("導入しない(SCAN 5891 行: PyPI の project_urls の綴りが 1 文字ずれ、配布元の一致が委任文 §6-1 の検査を通らない。導入は止めたまま、SCAN 5893 行)", "走らなかった", "導入前の検査を通せない"),
    107: ("項目0 の venv item_0/c107(cargo で構築した sigc)で走らせた", "走った", ""),
    109: ("導入しない(SCAN 10462 行: 論文で、実装への link が無い)", "走らなかった", "実装が無い"),
    111: ("導入も実行も (b) もしない", "走らなかった", "危険: 道具台帳 §3 の 11 件"),
    116: ("導入しない。R の package(SCAN 5246 行)で、この環境に R が無い", "走らなかった", "言語の実行系が無い"),
    119: ("git clone を読んだ(src/c119)。requirements は jax・jaxlob ほか(requirements.txt)で、生成の模型の出力を測る道具(impact.py 1-3 行)", "走らなかった", "埋まりを決める口が無い(測る側)"),
    123: ("導入しない(項目0 の記録を使う)", "走らなかった", f"危険(§6-1): {I0} の候補 123 の行(13 と同じ版・同じ postinstall)"),
}

# ------------------------------------------------------------------ hand-written rows of the not-run candidates
S = "SCAN"
RD = "(b) 一次資料を読んだ"


def low(c, cat, extra=""):
    x = cat[c]
    return ("スキップ: 明らかに弱い(段が低い)",
            f"段が低い: 段(機構) {x['mech'] or '空欄'}・段(既定) {x['dflt'] or '空欄'}(SCAN {x['trow']} 行)で、この観点の最も高い段 6"
            f"(動かせた 105・35・37・33・91・1・4・18、上位互換で外した 15・21・106・116)より低い{extra}")


def no_queue(c, cat):
    x = cat[c]
    return ("持たないと確認した",
            f"段(機構) {x['mech']}(SCAN {x['trow']} 行)で自分の注文の先行の列を追わず、先行注文の取消の扱いが立たない"
            f"(同じ段の表の行の取り消しの扱い: 「{x['cxl_raw'][:80]}」)")


def no_lat(c, cat, note=""):
    x = cat[c]
    return ("持たないと確認した",
            f"調べた範囲で遅延の模型が無い: SCAN {x['trow']} 行の遅延の欄「{x['lat_raw'][:110]}」{note}")


def facts(cat):
    F = {}

    def put(c, vps, mech, impl, verdict_reason):
        for v in vps:
            F[(c, v)] = (mech, impl) + verdict_reason

    tiers = lambda c: f"段(機構) {cat[c]['mech']}・段(既定) {cat[c]['dflt']}(SCAN {cat[c]['trow']} 行)"  # noqa: E731
    lat = lambda c: f"遅延の欄「{cat[c]['lat_raw'][:70]}」(SCAN {cat[c]['trow']} 行)"  # noqa: E731
    cxl = lambda c: f"取り消しの扱い「{cat[c]['cxl_raw'][:70]}」(SCAN {cat[c]['trow']} 行)"  # noqa: E731
    A = "(a) の書き写し"
    # ---- bar / low-tier candidates that could not be run: C2-5・C2-7 by tier, C2-6 no queue, C2-9 no latency
    for c in (7, 8, 13, 45, 50, 60, 67, 123):
        put(c, ("C2-5", "C2-7"), tiers(c), f"{A}(SCAN {cat[c]['row']}・{cat[c]['trow']} 行)", low(c, cat))
        put(c, ("C2-6",), cxl(c), f"{A}(SCAN {cat[c]['trow']} 行)", no_queue(c, cat))
        put(c, ("C2-9",), lat(c), f"{A}(SCAN {cat[c]['trow']} 行)", no_lat(c, cat))
    put(60, ("C2-9",), lat(60), f"{A}(SCAN 10503 行)",
        ("持たないと確認した", "遅延の模型が無い: SCAN 10503 行の遅延の欄は「別の意味の遅延」で、max_delay_count は埋まらなかった注文を次の足へ持ち越す回数の上限"))
    put(50, ("C2-9",), lat(50), f"{A}(SCAN 10529 行)",
        ("持たないと確認した", "遅延の模型が無い: SCAN 10529 行の遅延の欄「該当なし(文書上の主張)」の逐語 It does not take into consideration the market depth and liquidity"))
    for c in (19, 51, 111):  # 道具台帳 §3: (a) only
        put(c, ("C2-5", "C2-7"), tiers(c), f"{A}だけ(道具台帳 §3 の 11 件。導入も (b) もしない)",
            low(c, cat, "。道具台帳 §3 の 11 件で (b) はしない"))
        put(c, ("C2-6",), cxl(c), f"{A}だけ(道具台帳 §3)", no_queue(c, cat))
        put(c, ("C2-9",), lat(c), f"{A}だけ(道具台帳 §3)", no_lat(c, cat, "。道具台帳 §3 の 11 件で (b) はしない"))
    # ---- 97 (道具台帳 §3, (a) only): stance = 104's
    put(97, ("C2-5", "C2-7"), tiers(97), f"{A}だけ(道具台帳 §3)", low(97, cat, "。道具台帳 §3 の 11 件で (b) はしない"))
    put(97, ("C2-6",), cxl(97), f"{A}だけ(道具台帳 §3)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 97 の立場は SCAN 10537 行の逐語どおり「取り消しの時点で繰り上がる(104 の立場)」の 1 つだけで、"
         "動かせた 104 がその立場を持つ(SCAN 8820 行「取り消しが起きた時点で列が繰り上がる」、survey_results/opp_jxm35_lob.tsv の c2-6-l3 の行)"))
    put(97, ("C2-9",), lat(97), f"{A}だけ(道具台帳 §3)", no_lat(97, cat, "。道具台帳 §3 の 11 件で (b) はしない"))
    # ---- 38 MarS
    put(38, ("C2-5", "C2-7"), tiers(38), f"{A}(SCAN 9149・10514 行)", low(38, cat))
    put(38, ("C2-6",), cxl(38), f"{A}(SCAN 9149 行)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 38 の取消の扱いは SCAN 9149 行の逐語「取り消しが供給の側の注文として板に入る」(先行の注文が板から抜け、"
         "後ろが繰り上がる)の 1 つで、動かせた 104 が同じ立場を持つ(SCAN 8820 行、survey_results/opp_jxm35_lob.tsv の c2-6-l3 の行)"))
    put(38, ("C2-9",), lat(38), f"{A}(SCAN 9149 行)", no_lat(38, cat))
    # ---- 57 WonderTrader (reproduced; other viewpoints)
    put(57, ("C2-7",), tiers(57), f"{RD}(read/c57 の MatchEngine.cpp 1-372 行)", low(57, cat, "。影響の関数は MatchEngine.cpp に無い"))
    put(57, ("C2-9",), lat(57), f"{RD}(read/c57 の MatchEngine.cpp)",
        ("持たないと確認した", "遅延の模型が無い: MatchEngine.cpp(commit 08b230dd)1-372 行に遅延の語が無く、注文は次の tick で有効になるだけ(fire_orders 28-42 行)。SCAN 10516 行の遅延の欄も未確認(走査の当たり 0 件)"))
    # ---- 94 mote/backtest (reproduced; other viewpoints)
    put(94, ("C2-7",), tiers(94), f"{RD}(src/c94/backtest.py 427-457 行)", low(94, cat))
    put(94, ("C2-6",), cxl(94), f"{RD}(src/c94/backtest.py)", no_queue(94, cat))
    put(94, ("C2-9",), lat(94), f"{RD}(src/c94/backtest.py)", no_lat(94, cat, "。SCAN 10066 行: 走査した 1 本に遅延・滑り・手数料・出来高の語が 0 件"))
    put(94, ("C2-10",), "手数料の語が無い(SCAN 10066 行)", f"{RD}(src/c94/backtest.py)",
        ("持たないと確認した", "費用の口が無い: SCAN 10066 行の逐語「候補 94 には遅延・滑り・手数料・出来高の語が 1 つも無い」"))
    # ---- 63 trade-frame
    put(63, ("C2-5", "C2-7"), tiers(63), f"{A}(SCAN 7193・7548 行)", low(63, cat))
    put(63, ("C2-6",), cxl(63), f"{A}(SCAN 5703・10508 行)", no_queue(63, cat))
    put(63, ("C2-9",), "注文を時刻つきの遅延の列に入れ、気配の到着で取り出す(m_dtQueueDelay、既定 250 ミリ秒、SCAN 8126・7193 行)",
        f"{A}(SCAN 5702・7193・8126 行)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 63 の遅延は定数の発注の遅れ 1 つ(SCAN 7193 行 m_dtQueueDelay( milliseconds( 250 ) )、8126 行 SetOrderDelay)で、"
         "動かせた 37 が定数の発注の遅れを持つ(SCAN 10532 行 available_at = self._current_time + pd.Timedelta(milliseconds=int(self.latency_ms)))"))
    put(63, ("C2-1",), "成行・指値(と逆指値)を遅延の列で埋める(SCAN 5702・5777 行)", f"{A}(SCAN 5702・5777 行)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 成行と指値は動かせた 98 が持つ(SCAN 5282 行「指値・成行・IOC・FOK を 1 つの _match で扱う」)、"
         "逆指値は動かせた 20 が持つ(SCAN 6992 行「足とティックの両方で指値と逆指値を回し」)"))
    put(63, ("C2-2",), "注文の遅延の列からの取り出しと取消(SCAN 5702 行 m_lOrderDelay)", f"{A}(SCAN 5702・5703 行)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 自分の注文の取消は動かせた 98 が持つ(SCAN 5288 行「待ち行列を保つ取り消し」)。63 に訂正の記載は無い(SCAN 5702・5703 行)"))
    put(63, ("C2-10",), "CalculateCommission: 銘柄の種類ごとの 1 単位あたりの固定額(株・ETF 0.005 で最低 1.00、先物 2.20 ほか、通貨 0)を約定の量に掛ける(SimulateOrderExecution.cpp 81-115 行)",
        f"{RD}(read/c63/SimulateOrderExecution.cpp 33・81-115 行。raw の取得の記録は logs/i2_r1_scenekeeper_read.log)",
        ("持たないと確認した", "場面が測る費用の口が無い: 手数料は銘柄の種類で決まる 1 単位あたりの固定額だけで(SimulateOrderExecution.cpp 86-105 行)、"
         "maker と taker の率・スプレッド・資金調達・スワップ・JPX の料金表を渡す口が無く、値は既定で埋まる(33 行 m_dblCommission( 1.00 )。規則の「既定値を持たない」とも逆)"))
    # ---- 15 BacktestingCore
    put(15, ("C2-5", "C2-7"), "参加率の平方根の市場影響を実行経路が直に呼ぶ(SCAN 7555 行 calculate_market_impact)",
        f"{RD}(read/c15 backtest/src/simulation.rs 244-262・913 行)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 15 の影響は impact_bps(注文量, 平均出来高) の平方根の式 1 つ(SCAN 7555 行、simulation.rs 244-262 行)で、"
         "動かせた 33 が参加率の平方根の影響を実行経路で持つ(SCAN 7189 行 slippage_bps += volume_impact_factor_ * std::sqrt(participation))"))
    put(15, ("C2-6",), cxl(15), f"{RD}(read/c15 backtest/src/simulation.rs)",
        ("持たないと確認した", f"先行注文の取消の扱いが無い: SCAN {cat[15]['trow']} 行の取り消しの扱い「該当なし。当たり Cancelled, は振り分けの側の注文の状態」。"
         "合成の板は実行経路が呼ばない(SCAN 8806 行)"))
    put(15, ("C2-9",), "定数の latency_ms より後の注文だけを約定させる(simulation.rs 471-495 行)。揺らぎと跳ねの遅延(config/src/variable_latency.rs、SCAN 9013 行)は backtest/src から呼ばれない",
        f"{RD}(read/c15: grep で variable_latency の当たりは config/src の 2 本だけ)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 実行経路の遅延は定数 1 つ(simulation.rs 471-495 行)で、動かせた 33 が発注と取消の定数の遅れを持つ"
         "(SCAN 9150 行 submit_time = clock_.now() + config_.latency.order_submit_latency_ns)"))
    put(15, ("C2-1",), "信号の型 Buy・Sell・Close・ScaleIn・ScaleOut・StopLoss・TakeProfit・TwoSidedQuote(signal/src/lib.rs 35-49 行)を板の指値として出す"
        "(REQUIREMENTS.md が 15 に当てた SCAN 1819・1823 行は候補 1 Basana の節)", f"{RD}(read/c15 signal/src/lib.rs 35-49 行)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 指値は動かせた 98 が持つ(SCAN 5282 行)、損切り・利食いの逆指値は動かせた 20 が持つ(SCAN 6992 行)。"
         "両建ての気配(TwoSidedQuote)は指値 2 本で、98 の指値で出せる"))
    put(15, ("C2-2",), "自分の注文の取消(simulation.rs 730-735 行 OrderBookEvent::CancelOrder)", f"{RD}(read/c15 backtest/src/simulation.rs 730-735 行)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 自分の注文の取消は動かせた 98 が持つ(SCAN 5288 行)。訂正の口は simulation.rs に無い"))
    put(15, ("C2-10",), "約定ごとの fee_amount と既定の commission_rate(simulation.rs 195-196・575-592 行)",
        f"{RD}(read/c15 backtest/src/simulation.rs 195-196・575-592 行)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 約定ごとの率の手数料は動かせた 20 が持つ(SCAN 1269 行「約定ごとの滑りと手数料を rate / slippage / pricetick の形で分けて持つ」)"))
    # ---- 21 Qlib ran (probe) -> automatic rows; 36 / 106 / 116 / 119 / 100 / 109
    put(36, ("C2-5", "C2-7"), "temporary_impact = eta * sigma * np.sign(x) * np.power(np.abs(x) , beta) を実データに当てはめる(SCAN 7191・7560 行)",
        f"{RD}(src/c36/impactModel.py 65-81 行)",
        ("持たないと確認した", "約定を決める口が無い: SCAN 7191 行の逐語「検証の機関ではなく、係数 eta と beta を推定する当てはめの手続きである」。"
         "impactModel.py はモジュールの頭で Input/*.csv を読み curve_fit の結果を表示するだけ(1-9・65-81 行)"))
    put(36, ("C2-6",), cxl(36), f"{RD}(src/c36/impactModel.py)", ("持たないと確認した", "先行の列を持たない: 当てはめの台本だけ(SCAN 7191 行、impactModel.py 1-81 行)"))
    put(36, ("C2-9",), lat(36), f"{RD}(src/c36/impactModel.py)", no_lat(36, cat, "。impactModel.py は当てはめの台本(SCAN 7191 行)"))
    for c, ln in ((106, "5893・5895"), (116, "5572")):
        put(c, ("C2-5", "C2-7"), f"Almgren-Chriss の線形の恒久 g(v) = γv と一時 h(v) = ε sgn + ηv(SCAN {ln} 行)", f"{A}(SCAN {ln} 行。(a) で式が足りた)",
            ("スキップ: 明らかに弱い(上位互換)", f"上位互換: {c} の影響は線形の恒久と一時の 2 本だけ(SCAN {ln} 行。5572 行「候補 105 と同じ 2 分割だが、105 が平方根則・べき乗則も持つのに対し 116 は線形のみ」、"
             "5895 行「候補 106 と同じ模型」)で、動かせた 105 が LinearImpact の恒久と一時を持つ(SCAN 5222 行)"))
        put(c, ("C2-6",), cxl(c), f"{A}(SCAN {ln} 行)", ("持たないと確認した", f"先行の列を持たない: 影響の式の道具で約定の列が無い(SCAN {ln} 行)。SCAN {cat[c]['trow']} 行の取り消しの扱いも走査の当たり 0 件"))
        put(c, ("C2-9",), lat(c), f"{A}(SCAN {ln} 行)", no_lat(c, cat, "。影響の式の道具(執行の時間の分割を解く)"))
    put(119, ("C2-5", "C2-7"), "生成の模型の出力と実データの市場影響の応答を比べて測る(SCAN 9405 行、impact.py 1-3 行)", f"{RD}(src/c119/impact.py 1-3・27-75 行)",
        ("持たないと確認した", "約定を決める口が無い: SCAN 9405 行「119 番は『測る側』であって埋まりを決めていない」。impact.py 1-3 行の逐語 Functions to estimate market impact of different events produced by the model"))
    put(119, ("C2-6",), cxl(119), f"{RD}(src/c119)", ("持たないと確認した", f"先行注文の取消の扱いが無い: SCAN {cat[119]['trow']} 行「別の意味の取り消し」(生成の模型の尺度の名)"))
    put(119, ("C2-9",), lat(119), f"{RD}(src/c119)", no_lat(119, cat))
    put(100, ("C2-5", "C2-7"), "照合の 4 関数の本体が空(SCAN 10447 行)", f"{A}(SCAN 10447・10477 行)",
        ("持たないと確認した", "埋まりを決める本体が無い: SCAN 10477 行「付けない。該当なし(公開された原典に埋まりを決める本体が無い)」、10447 行"))
    put(109, ("C2-5", "C2-7"), "生成の模型で先の板の状態を作る論文(SCAN 10462 行)", f"{A}(SCAN 10462・10482 行)",
        ("持たないと確認した", "注文を入れて埋まりを決める口が無い: SCAN 10482 行「付けない。該当なし(注文を入れて埋まりを決める口が無い)」"))
    # ---- 45 / 50 (web products): order types by the text only
    for c, ln in ((45, "10060・10186"), (50, "10186・10088")):
        put(c, ("C2-1", "C2-2"), f"未約定の注文と、値幅の外に出た逆指値が指値として残る振る舞いを文書で主張(SCAN {ln} 行)", f"{A}(SCAN {ln} 行、文言だけ)",
            ("再現できない", f"(a) SCAN {ln} 行は場の画面の文言だけで、注文を埋める式が無い。(b) 一次資料はウェブの場で、実装のコードが公開されていない(SCAN 10082・10088 行)"))
    # ---- 58 nautilus (道具台帳 §3)
    put(58, ("C2-1", "C2-2"), "IOC・FOK・GTC・GTD・DAY・post-only・reduce-only・OCO ほかを名乗る(SCAN 247 行、PyPI の説明の逐語)", f"{A}だけ(道具台帳 §3)",
        ("再現できない", "危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) SCAN 247 行は PyPI の説明の逐語だけで、注文を埋める実装の書き写しが無い"))
    # ---- 94 C2-1 / C2-2 reproduced: automatic.  C2-10 / C2-11
    put(7, ("C2-10",), "約定の模擬を実際の大きさ・実際の値・手数料・埋まった割合の 4 関数に分け、滑りを設定から差し引く(SCAN 6986 行)", f"{A}(SCAN 6986 行)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 手数料と滑りは動かせた 20 が分けて持つ(SCAN 1269 行 rate / slippage)。埋まった割合は費用の能力でない(約定の量は C2-5 の段で扱う)"))
    put(11, ("C2-10",), "FEE の辞書で約定ごとの手数料を持つ(SCAN 4135 行)", f"{A}(SCAN 4135 行)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 約定ごとの率の手数料は動かせた 1 が持つ(SCAN 1666 行 fees.Percentage(0.05%))。maker と taker を分けた率は動かせた 37 が持つ"
         "(survey_results/opp_predictivedev_tradesim.tsv の c2-10-maker・c2-10-taker の行が正解と一致)"))
    put(11, ("C2-11",), "現物の残高(PF_START / PF_AFTER の資産の辞書)で建玉を持つ(SCAN 4135 行)", f"{A}(SCAN 4135 行)",
        ("スキップ: 明らかに弱い(上位互換)", "上位互換: 残高と建玉と実現・評価の損益は動かせた 37 が持つ(survey_results/opp_predictivedev_tradesim.tsv の c2-11-pnl の行が正解と一致)。"
         "11 の口座の記載は現物の残高だけ(SCAN 4135 行)"))
    for c, ln in ((13, "6989"), (123, "6651")):
        put(c, ("C2-10",), f"模擬の取引所で maker と taker の約定・滑り・手数料を入れる(SCAN {ln} 行)", f"{A}(SCAN {ln} 行)",
            ("スキップ: 明らかに弱い(上位互換)", f"上位互換: maker と taker の手数料は動かせた 37 が持つ(survey_results/opp_predictivedev_tradesim.tsv の c2-10-maker・c2-10-taker の行)、"
             f"滑りは動かせた 20 が持つ(SCAN 1269 行)。{c} の費用の記載はこの 3 つ(SCAN {ln} 行)"))
    for c in (19, 41):
        put(c, ("C2-10",), f"SCAN {'1226・7147' if c == 19 else '4112'} 行の書き写し", f"{A}だけ(道具台帳 §3)",
            ("再現できない", f"危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) SCAN {'1226・7147' if c == 19 else '4112'} 行は説明の文だけで、費用の式の書き写しが無い"))
    put(19, ("C2-11",), "取引所ごとの手数料・レバレッジ・証拠金の型(SCAN 1226 行)", f"{A}だけ(道具台帳 §3)",
        ("再現できない", "危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) SCAN 1226 行は説明の文だけで、証拠金の式の書き写しが無い"))
    put(51, ("C2-11",), "指定の値で約定させる(SCAN 9404 行)", f"{A}だけ(道具台帳 §3)",
        ("再現できない", "危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) SCAN 9404 行は約定の逐語だけで、口座の式の書き写しが無い"))
    put(40, ("C2-10", "C2-11"), "「資金調達率・清算・不利な価格での約定を含む模擬」と主張(SCAN 4111 行、X の投稿)", f"{A}(SCAN 4111 行)",
        ("再現できない", "(a) SCAN 4111 行は宣伝の投稿の主張だけで式が無い。(b) 一次資料は場の頁で、code や文書への参照が 0 件(tests/bt/battery/item_0/opponents/RUNNABILITY.tsv の候補 40 の行)"))
    return F


GONE_NOTE = "。結果を取ったあと(2026-09-25 18:28Z までに)この venv は他の役に消された(この役は消していない。消えたあとは入れ直すまで走らせ直せない)"
GONE = {2, 20, 34, 35, 37, 65, 105, 107}  # venvs removed after this role's last run of them (3, 4, 10, 16, 18, 53, 87 say so in RUN)


def main():
    for c in GONE:
        t, r, why = RUN[c]
        RUN[c] = (t + GONE_NOTE, r, why)
    cat = catalog()
    pl, names = pool()
    res = results()
    real, repro = targets_by_cand()
    F = facts(cat)

    def got(tgts, v):
        return any(cls != "結果なし" for t in tgts for _s, cls, _d in res.get(t, {}).get(v, []))

    # RUNNABILITY.tsv
    cands = sorted({c for v in VPS for c in pl[v]})
    with open(HERE / "opponents" / "RUNNABILITY.tsv", "w", encoding="utf-8") as fh:
        fh.write("cand\tname\ttried\tresult\ttargets\treason\n")
        for c in cands:
            tried, result, reason = RUN.get(c, ("(記録なし)", "?", ""))
            tg = ",".join(real.get(c, []) + repro.get(c, [])) or "-"
            fh.write(f"{c}\t{names[c]}\t{tried}\t{result}\t{tg}\t{reason or '-'}\n")
    missing = [c for c in cands if c not in RUN]
    # CONSIDERED.md
    out = ["# 項目 2「執行の模型」— 動かせなかった候補の検討表", "",
           "場面係が書く(委任文 §3「動かせない候補の検討と再現」・場面集の規則 6・9)。この表は `tests/bt/battery/item_2/gen_considered.py` が作る。", "",
           "- 候補 = `pool.tsv`(REQUIREMENTS.md §3 の機械の抜き出し。`gen_pool.py`)。導入の記録は `opponents/RUNNABILITY.tsv`(候補ごとに 1 行)。",
           "- 「動かせた候補」= 実物の道具の対象(i2_targets.py)が走り、その観点の場面で「結果なし」以外を 1 つ以上返した候補(`survey_results/<対象>.tsv` から機械で数えた)。"
           "走ったが、その観点の場面が全部「結果なし」だった候補は、その観点では表の行に載せ、adapter の理由(実際に呼んだ結果)を根拠にする(規則 4 の「候補ごとの欠け」と「場面ごとの欠け」を分ける)。",
           "- 再現 = 一次資料どおりの最小の書き直し(`opponents/repro_*.py`)。再現の対象は表の上では他の道具と区別しない(資料係の記録にだけ残す)。",
           "- 段のある観点 = C2-5・C2-7(REQUIREMENTS.md §3.1)。C2-6 は 5 つの立場に順位が無い(REQUIREMENTS.md §3.1)ので段で外さない。C2-9 は遅延の模型の有無で見る。",
           "- SCAN = `docs/DATA/SCAN_2026-09-21_tools.md`、段の値と「SCAN 105xx 行」= `docs/DATA/tools_catalog.tsv` の列 10・11・18。",
           "- REQUIREMENTS.md の候補の行のうち、本表で読み替えたもの(リードに聞くこと): C2-1 の「15 BacktestingCore(SCAN 1819・1823 行)」の 2 行は候補 1 Basana の節"
           "(1819 行「backtesting の取引所(成行・指値・逆指値・逆指値付き指値の 4 種の注文…」、1823 行 VolumeShareImpact)。候補 5 は台帳の名が Lean CLI だが SCAN 6849 行の名は bt"
           "(本表と RUNNABILITY.tsv は bt として扱った)。§3.1 の「52 件」の awk は列の名が 1 つずれている($9 = 市場影響と約定の模型、$10 = 段(機構))。", ""]
    for v in VPS:
        rows = []
        ran_ok = [c for c in pl[v] if got(real.get(c, []), v)]
        for c in pl[v]:
            if c in ran_ok:
                continue
            nm = f"{c} {names[c]}"
            if got(repro.get(c, []), v):
                t = repro[c][0]
                mod = T.SURVEY[t]["module"] if t in getattr(T, "SURVEY", {}) else T.TARGETS[t]["module"]
                hits = [s for s, cls, _d in res[t][v] if cls != "結果なし"]
                rows.append((nm, "一次資料の実装の該当の関数(再現の注釈に行ごとに書いた)", "(b) 一次資料のコードを読んだ", "再現した",
                             f"{mod} を `run_battery.py --target {t}` で場面に通した(この観点の {', '.join(hits)} に結果)。根拠の URL と行は {mod} の注釈"))
                continue
            if (c, v) in F:
                mech, impl, verdict, why = F[(c, v)]
                rows.append((nm, mech, impl, verdict, why))
                continue
            tg = real.get(c, [])
            if tg:
                reasons = []
                for t in tg:
                    for _s, _cls, d in res.get(t, {}).get(v, []):
                        d = d.split("試したこと")[0].replace("adapter: ", "").replace("|", "/").strip()
                        if d and d not in reasons:
                            reasons.append(d)
                x = cat.get(c, {})
                mech = (f"段(機構) {x.get('mech') or '空欄'}・段(既定) {x.get('dflt') or '空欄'}・遅延 {x.get('lat') or '空欄'}・取消 {x.get('cxl') or '空欄'}"
                        f"(SCAN {x.get('trow') or x.get('row')} 行)")
                why = (f"場面が測る能力の口が無い: `python3 tests/bt/battery/item_2/run_battery.py --target {tg[0]} --out …` の出力 survey_results/{tg[0]}.tsv の"
                       f" {v} の行が全部「結果なし」。adapter の理由(道具を実際に呼んだ結果): " + " / ".join(reasons[:3])[:600])
                rows.append((nm, mech, f"実装を呼んだ(対象 {', '.join(tg)})", "持たないと確認した", why))
                continue
            rows.append((nm, "(未記入)", "(未記入)", "(未記入)", "(未記入)"))
        out.append(f"### 観点 {v} {VP_NAME[v]}")
        out.append("")
        out.append(f"動かせた候補: {len(ran_ok)} 件" + (f"({', '.join(f'{c} {names[c]}' for c in ran_ok)})" if ran_ok else ""))
        out.append("")
        if not pl[v]:
            out.append(f"候補 0 件: `{ZERO.get(v, 'pool.tsv')}`")
            out.append("")
            continue
        if not rows:
            out.append(f"動かせなかった候補 0 件: `awk -F'\\t' '$1==\"{v}\"' tests/bt/battery/item_2/pool.tsv`(候補は全部動かせた)")
            out.append("")
            continue
        out.append("| 候補 | 機構 | 実装 | 判断 | 理由 |")
        out.append("|---|---|---|---|---|")
        for r in rows:
            out.append("| " + " | ".join(str(x).replace("|", "/").replace("\n", " ") for x in r) + " |")
        out.append("")
    path = HERE / "opponents" / "CONSIDERED.md"
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    tail = old[old.index("<!-- 集計ここから -->"):] if "<!-- 集計ここから -->" in old else ""
    path.write_text("\n".join(out) + "\n" + tail, encoding="utf-8")
    if missing:
        print("RUN に記録の無い候補:", missing)
    print(path)


if __name__ == "__main__":
    main()
