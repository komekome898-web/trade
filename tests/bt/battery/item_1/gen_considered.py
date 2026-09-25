#!/usr/bin/env python3
"""Write opponents/CONSIDERED.md (item 1) from the rows below, then run
scripts/check_bt_considered.py --write on it (the aggregate block is the tool's).

Which candidates are "動かせた" in a viewpoint is read from survey_results/opp_*.tsv
(a candidate that produced at least one result other than 「結果なし」 in that
viewpoint's scenes); every other candidate of REQUIREMENTS.md §3 is a row.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))

import i1_scenes as S  # noqa: E402
import i1_targets as T  # noqa: E402

NAMES = {3: "PySystemtrade", 12: "pybotters", 20: "VnPy", 21: "Qlib", 23: "hftbacktest", 54: "finmarketpy",
         55: "backtesting.py", 61: "barter-rs", 73: "vectorbt", 74: "ml-quant-trading", 87: "PyTrendFollow",
         105: "DaniyalMlk/slippage", 121: "mhallsmoore/qstrader"}
VP = ["V1", "V2", "V3", "V4", "V5", "V6", "V7"]
VEN = "<venvs>"  # = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs

RUN = "`run_battery.py --target {t}` の出力 survey_results/{t}.tsv の {vp} の場面が全部「結果なし」(adapter の理由: {why})"
IMPL = "実装のコードで確かめた({where})"
A_ONLY = "(a) の書き写しだけ(道具台帳 §3 の 11 件。導入も一次資料の読みもしない)"

# ---- facts per candidate (installed code read 2026-09-25; lines are file:line in the installed copy)
READER = {
    3: ("先物の足の CSV の読み口 csvFuturesContractPriceData + ConfigCsvFuturesPrices(日付の索引 1 列・日付の書式・列の対応)", f"{VEN}/item_0/_dl/c3/sysdata/csv/csv_futures_contract_prices.py 17-27 行"),
    12: ("HTTP / WebSocket の通信と DataStore だけ。ファイルの読み口なし(grep read_csv・csv.reader 0 件)。時刻の文字列は変換せずに持つ(SCAN 2788 行)", f"{VEN}/item_0/pybotters/…/pybotters"),
    20: ("本体と vnpy_ctastrategy にファイルの読み口なし(grep read_csv・csv.reader 0 件)。足は BarGenerator.update_tick(vnpy/trader/utility.py 166・204 行)の 1 本道", f"{VEN}/item_0/vnpy/…/vnpy/trader/utility.py 166・204 行"),
    21: ("配布物に CSV の読み口なし(read_csv の当たりは銘柄の一覧 file_storage.py 208 行・暦 utils/__init__.py 602 行・注文・予測の表)。CSV から自前の形に直す dump_bin.py はリポジトリの scripts/ にあり配布物に無い", f"{VEN}/item_1/qlib/…/qlib/data/storage/file_storage.py 208 行"),
    23: ("取引所・業者ごとに形が固定の変換器(data/utils/tardis.py 56 行 convert は Tardis の trades / incremental_book_L2 の CSV)。列の対応・単位・時間帯の引数なし", f"{VEN}/item_0/hftbacktest/…/hftbacktest/data/utils/tardis.py 56 行"),
    54: ("findatapy の IOEngine.read_csv_data_frame(ioengine.py 1080 行。最初の列を時刻の索引、ほかの列を float32 = 1130 行、時刻の読み方は日付の文字列の型だけ = 1108-1121 行)", f"{VEN}/item_0/finmarketpy/…/findatapy/market/ioengine.py 1080・1108-1130 行"),
    55: ("読み口なし。Backtest(backtesting.py 1111 行)はメモリ上の OHLC の DataFrame を取る(read_csv の当たりは同梱の例の test/__init__.py だけ)", f"{VEN}/item_0/backtesting/…/backtesting/backtesting.py 1111 行"),
    61: ("ファイルの読み口なし(grep csv::Reader・ReaderBuilder 0 件)。型つきの MarketEvent の列を受ける。Candle は close_time: DateTime<Utc>(SCAN 6303 行)", f"{VEN}/item_0/_dl/c61"),
    73: ("市場データのファイルの読み口なし(grep read_csv・class CSVData 0 件。data の型は合成と取得だけ: data/custom.py 29 行 SyntheticData・183 行 YFData・301 行 BinanceData・556 行 CCXTData・759 行 AlpacaData)", f"{VEN}/item_1/vectorbt/…/vectorbt/data/custom.py"),
    87: ("任意の CSV の読み口なし(grep read_csv・DictReader・csv.reader 0 件。データは IB と Quandl からの取得を自前で保管: config/currencies.py 9-12 行)", f"{VEN}/item_0/_dl/c87"),
    105: ("読み口の列が固定(足 = symbol,timestamp,open,high,low,close,volume、io.py 44 行。欠けると InputError、57-59 行)。時刻は datetime.fromisoformat(133 行)", f"{VEN}/item_0/c105/…/slippage/io.py 44・57-59・126-149 行"),
    121: ("CSVDailyBarDataSource(qstrader/data/daily_bar_csv.py 35・44-54 行)は <銘柄>.csv の日足で列が固定(Date, Open, High, Low, Close, Adj Close, Volume)", f"{VEN}/item_0/qstrader/…/qstrader/data/daily_bar_csv.py 35・44-54 行"),
}
TARGET_OF = {v["cand"]: k for k, v in T.SURVEY.items() if not v.get("repro")}
SCAN74 = {
    "V1": "入力は重みと収益の行列(SCAN 5885 行「weights : np.ndarray [T, N]」「returns : np.ndarray [T, N]」)で、ファイルの読み口の記載なし",
    "V2": "粒度は日(SCAN 5886 行「単位は日で、足より細かい入力の口が無い」)。時刻の単位の正規化の記載なし",
    "V3": "計算の本体は行列の演算だけ(SCAN 5885 行)。重複・逆行・欠落・世代の検査の記載なし",
    "V4": "書き写し(SCAN 5885・5886・5888 行)に読んだデータのハッシュを記録する記載なし",
    "V5": "書き写し(SCAN 5885・5886 行)にデータのパスを拒む許可一覧の記載なし",
    "V6": "生存者の偏りなどの前提は文書に列挙するだけで実装していない(SCAN 5888 行「足しなさい」の一覧、5944 行「前提を報告の必須項目として一覧にしている運用」)",
    "V7": "「Vectorised backtest engine.」で時間の繰り返しが 1 つも無い(SCAN 5885 行)= 突き合わせる事象駆動の経路が無い",
}


def rows_for(vp: str, runnable: set[int]) -> list[tuple]:
    out = []
    for c in sorted(NAMES):
        if c in runnable:
            continue
        name = f"{c} {NAMES[c]}"
        if c == 74:
            out.append((name, SCAN74[vp], A_ONLY, "持たないと確認した", f"{SCAN74[vp]}。導入も実行もしない(委任文 §4)"))
            continue
        tgt = TARGET_OF[c]
        rd, where = READER[c]
        why = _why(tgt, vp)
        run = RUN.format(t=tgt, vp=vp, why=why)
        if vp == "V3" and c in (23, 105):
            f = {23: "opponents/repro_23_event_order.py", 105: "opponents/repro_105_duplicate_bars.py"}[c]
            mech = {23: f"事象の順の検査 validate_event_order(exch_ts が戻れば ValueError。報告は無い)({VEN}/item_0/hftbacktest/…/hftbacktest/data/validation.py 139-152 行)",
                    105: f"足の系列 BarSeries(時刻で並べ替え、同じ時刻の足があれば ValidationError。報告は無い)({VEN}/item_0/c105/…/slippage/series.py 35-41 行)"}[c]
            out.append((name, mech, IMPL.format(where=mech.split("(")[-1].rstrip(")")), "再現した",
                        f"道具の読み口がこの場面の形を取れない({rd})ため、検査の機構だけを一次資料(導入済みのコード)どおりに書き直し、{f} として全場面に通した"
                        f"(survey_results/opp_repro_{c}.tsv)。{run}"))
            continue
        mech, reason = _mech(c, vp, rd)
        out.append((name, mech, IMPL.format(where=where), "持たないと確認した", f"{reason}。{run}"))
    return out


def _why(tgt: str, vp: str) -> str:
    p = HERE / "survey_results" / f"{tgt}.tsv"
    for r in csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"):
        if r["viewpoint"] == vp:
            return r["detail_1"].replace("adapter: ", "").replace("|", "/")[:160]
    return "-"


def _mech(c: int, vp: str, rd: str):
    if vp == "V1":
        return rd, f"場面が測る「宣言(spec)だけで資産の違うファイルを共通の事象にする」口が無い: {rd}"
    if vp == "V2":
        extra = {
            12: "時刻の文字列を変換しない(SCAN 2788 行)",
            54: "時刻は最初の列だけ・日付の文字列の型だけ(\"dukascopy\" は秒まで、既定は DD/MM/YYYY。ioengine.py 1108-1121 行)。数の単位・時間帯の引数なし",
            61: "時刻の口は秒(f64)とミリ秒の 4 関数だけ(barter-integration/src/serde/de/util.rs 20・32・44・56 行)。マイクロ・ナノ・時間帯の口なし",
            105: "時刻は ISO だけ(io.py 133 行 datetime.fromisoformat)。秒・ミリ・マイクロ・ナノの口と時間帯の引数なし",
            23: "時刻は変換器ごとの固定(tardis.py 56 行以下はマイクロ秒の整数)。単位・時間帯の引数なし",
            3: "日付の索引 1 列と日付の書式だけ(csv_futures_contract_prices.py 17-24 行)。数の単位・時間帯・2 列の口なし",
            121: "日足の Date 列だけ(daily_bar_csv.py 35 行以下)。日中の時刻・単位・時間帯の口なし",
        }.get(c, "ファイルの時刻を読む口が無い(V1 の行)")
        return rd, f"場面が測る「秒・ミリ・マイクロ・ナノ・ISO の同じ瞬間を同じ UTC のナノ秒に」の口が無い: {extra}"
    if vp == "V3":
        extra = {
            3: "重複は結合のときに黙って落とす(sysdata/futures/futures_per_contract_prices.py 381 行 index.duplicated(keep=\"first\"))。報せる口なし",
            55: "索引が増えているかを見るだけ(backtesting.py 1252 行 is_monotonic_increasing)。重複・欠落・世代を報せる口なし",
            21: "読み口が無い(V1 の行)。data の重複の当たりは列の重複(data/cache.py 923 行)だけ",
        }.get(c, "重複・逆行・欠落・世代の食い違いを報せる口が無い(読み口の行は V1 の行)")
        return rd, f"場面が測る「仕込んだ異常を種類と時刻で報せる」口が無い: {extra}"
    if vp == "V4":
        extra = {
            12: "hashlib の当たりは取引所への署名(pybotters/helpers/hyperliquid.py 39・281 行)だけ",
            21: "hashlib の当たりは文字列の md5(キャッシュの名前、qlib/utils/__init__.py 274 行)だけ",
            61: "sha の当たりは署名つきの要求の例(barter-integration/examples/signed_get_request.rs)だけ",
        }.get(c, "grep -rlnE 'sha256|hashlib' の当たり 0 ファイル")
        return rd, f"場面が測る「読んだファイルごとの sha256 を実行の記録に残す」口が無い: {extra}。読み口は V1 の行のとおり"
    if vp == "V5":
        extra = {
            121: "読み口は csv_dir の下の CSV を全部読む(daily_bar_csv.py 44-54 行 os.listdir)",
            3: "読み口は datapath の下を名前の規則で読む(csv_futures_contract_prices.py 27 行以下)",
        }.get(c, "パスを拒む語(allowlist・whitelist・qa_・o3c・phase2・sealed)の当たりは無関係の箇所だけ")
        return rd, f"場面が測る「合成・中間物・封印区間のパスを構造で拒む」口が無い: {extra}。読み口は V1 の行のとおり"
    if vp == "V6":
        extra = {
            121: "調整はファイルの Adj Close の比を掛けるだけ(daily_bar_csv.py 134-161 行)。DynamicUniverse は入る日だけで除く口が無い(asset/universe/dynamic.py 9-10 行「does not currently support removal of assets」)。コード変更の口なし",
            73: "調整の種類を渡す引数は Alpaca からの取得(data/custom.py 838 行、鍵が要る)で、取得先が調整する。分割の事象から自前で調整する口・日付ごとの銘柄集合の口なし",
            3: "先物の道具(SCAN 3168〜3254 行「同梱の先物の価格データが 252 銘柄」)で、個別株の分割・併合・上場廃止・コード変更の当たり 0 件",
            87: "先物の道具(config/instruments.py 24 行 point_value「on the futures contract」、config/spots.py 3 行)で、個別株の分割・併合・上場廃止・コード変更の当たり 0 件",
        }.get(c, "分割・併合・上場廃止・コード変更・生存者の当たり 0 件(grep -rniE の語 delist・survivor・corporate action・stock split・reverse split)")
        return rd, f"場面が測る「分割・併合・コード変更の調整と、日付ごとの上場銘柄の集合」の口が無い: {extra}。扱う入力は {rd}"
    extra = {
        3: "模擬は pandas のベクトル化の 1 経路(SCAN 9401 行の節)",
        12: "模擬の経路が無い(通信の道具。SCAN 6871 行の節)",
        20: "足づくり BarGenerator.update_tick(utility.py 204 行)と CTA の検証は 1 本ずつの 1 経路",
        21: "検証は qlib.backtest の 1 経路(qlib/backtest/__init__.py 217 行 backtest)",
        23: "ティックごとの事象駆動の 1 経路(SCAN 6906 行の節)",
        54: "信号の表と値の表の演算の 1 経路(SCAN 7851 行「区分1-イベント駆動 は付けない」)",
        55: "Strategy.next を足ごとに呼ぶ 1 経路(backtesting.py 1271 行 run)",
        61: "事象駆動の 1 経路(SCAN 6926 行の節、型つきの MarketEvent の列を受ける)",
        87: "accountCurve(trading/accountcurve.py 12 行)のベクトル化の 1 経路",
        105: "足の系列から執行費用を出す道具で、模擬の 2 経路が無い",
        121: "日程で駆動する 1 経路(qstrader/trading/backtest.py 25 行 BacktestTradingSession・368 行 run、simulation/daily_bday.py 11 行)",
    }[c]
    return rd, f"場面が測る「同じ足を事象駆動と近道の 2 経路で回して一致させる」口が無い: {extra}"


def runnable_by_vp() -> dict[str, set[int]]:
    out = {v: set() for v in VP}
    for tgt, spec in T.SURVEY.items():
        if spec.get("repro"):
            continue
        p = HERE / "survey_results" / f"{tgt}.tsv"
        for r in csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"):
            if r["class_1"] != "結果なし" or r["class_2"] != "結果なし":
                out[r["viewpoint"]].add(spec["cand"])
    return out


def main() -> int:
    run = runnable_by_vp()
    lines = ["# 項目 1「データと時刻」— 動かせなかった候補の検討表", "",
             "場面係が書く(委任文 §3「動かせない候補の検討と再現」・場面集の規則 6・9)。この表は `tests/bt/battery/item_1/gen_considered.py` が作る。",
             "", "- 候補 = REQUIREMENTS.md §3 が名を挙げた 13 件(§3.2 の機械抽出 54・73・74・87、§3.3 の grep の当たり 23・12・55・121・20・105・61・3・21)。",
             "  §3.4 の番号の並び「5・7」は、§3.3 が名を付けた候補(L584 の Backtesting.py = 台帳 55、L614 の QSTrader = 台帳 121)と読んだ(台帳の 5 は Lean CLI、7 は Superalgos で、§3 のどこにも名が出ない)。「その他」は数えられないので含めていない(リードに聞くこと)。",
             "- 「動かせた候補」= 隔離した venv で動き、その観点の場面で「結果なし」以外を 1 つ以上返した候補(survey_results/opp_*.tsv から機械で数えた)。導入はできたが、その観点の場面を 1 つも取れなかった候補は、その観点では表の行に載せる(規則 4 の「候補ごとの欠け」)。",
             "- 段: どの観点にも無い(REQUIREMENTS.md §3.1。`段(機構)`・`段(既定)` は約定の模型の観点だけの列)。だから「段が低い」を理由にしたスキップは 1 件も無い。",
             f"- 実装の列の {VEN} は `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs`、「…」は `lib/python3.11/site-packages`。",
             "- 「持たないと確認した」の根拠は、導入済みの道具では adapter が実際に呼んだ結果(survey_results の表)と導入済みのコードの行、74 は SCAN の書き写しの行。", ""]
    for vp in VP:
        lines.append(f"### 観点 {vp} {S.VIEWPOINTS[vp]}")
        lines.append("")
        ids = sorted(run[vp])
        lines.append(f"動かせた候補: {len(ids)} 件" + (f"({', '.join(f'{c} {NAMES[c]}' for c in ids)})" if ids else ""))
        lines.append("")
        lines.append("| 候補 | 機構 | 実装 | 判断 | 理由 |")
        lines.append("|---|---|---|---|---|")
        for r in rows_for(vp, run[vp]):
            lines.append("| " + " | ".join(x.replace("|", "/").replace("\n", " ") for x in r) + " |")
        lines.append("")
    lines += ["<!-- 集計ここから -->", "<!-- 集計ここまで -->", ""]
    out = HERE / "opponents" / "CONSIDERED.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "check_bt_considered.py"), str(out), "--write"], capture_output=True, text=True)
    print(r.stdout[-2000:], r.stderr[-2000:])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
