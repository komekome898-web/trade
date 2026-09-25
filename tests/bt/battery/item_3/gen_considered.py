#!/usr/bin/env python3
"""Write tests/bt/battery/item_3/opponents/CONSIDERED.md (the review table of the candidates that could not be run).

    python3 tests/bt/battery/item_3/gen_considered.py
    python3 scripts/check_bt_considered.py tests/bt/battery/item_3/opponents/CONSIDERED.md --write

Candidates = every tool REQUIREMENTS.md §3.3 names (16, one of them without a catalogue number).
For each viewpoint C3-1..C3-19:
- a candidate installed in an isolated venv is 「動かせた」 in that viewpoint when at least one of the
  viewpoint's scenes ended in something other than 「結果なし」 in survey_results/<target>.tsv (counted here,
  never typed); otherwise it gets a row 「持たないと確認した」 whose reason is what its adapter found when the
  scenes were run (the tool's code searched, the lines that show there is no mouth);
- a candidate reproduced from its primary source gets 「再現した」 in the viewpoints where its reproduction
  returned a result, and 「持たないと確認した」 (the source's lines) elsewhere;
- a candidate neither installed nor reproduced gets the judgement written in NOT_RUN from reading its
  primary source ((b)) or, for the survey's 11 dangerous candidates, the survey report only ((a)).
The aggregate block is written by scripts/check_bt_considered.py --write, not here.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import i3_scenes as S  # noqa: E402

RES = HERE / "survey_results"
OUT = HERE / "opponents" / "CONSIDERED.md"
URL15 = "https://github.com/Mendl-Labs/BacktestingCore/tree/f8d81ee0b4b65f6fbbf205d011ad2e815054fbc7"
URL8 = "https://github.com/bludnic/OpenTrader/tree/8b8e24599599df214b12b4263553885854015b4b"
URL88 = "https://github.com/rmbell09-lang/tradesight/tree/8b2de128b5180d05e87a51a191685298e2e888e6"

# (number, name, kind, target, mechanism, implementation)
CANDS = [
    (15, "Mendl-Labs/BacktestingCore", "repro", "opp_repro_15",
     "Rust の作業空間(walkforward・metrics・backtest の crate)。walk-forward の窓・CPCV の折り目と purge・PBO・DSR 2 通り・最大ドローダウン・約定率を持つ",
     f"実装のコードで確かめた(一次資料 {URL15} を読むだけの複製 <read>/BacktestingCore)"),
    (107, "sigc", "run", "opp_sigc",
     "日足の価格の表の上の信号の言語(.sig)のコンパイラと実行器。sigc run --trials で自分のバックテストの Sharpe を試行の数で縮め、sigc diff で 2 つの報告を比べる",
     "実装で確かめた(<venvs>/item_0/c107/bin/sigc を呼んだ。ソースの複製はリードの容量の片付けで消えていた)"),
    (0, "mlflow", "run", "opp_mlflow",
     "実験の記録係(パラメータ・指標・成果物・札・実行の識別子、git の commit の札を自分で付ける)。バックテストも統計の検証も持たない",
     "実装のコードで確かめた(<venvs>/item_3/mlflow/…/mlflow)"),
    (3, "PySystemtrade", "run", "opp_pysystemtrade",
     "先物の系統的な売買の枠組み(予測値 → 建玉 → 口座の曲線)。当て嵌めの期間は年単位(sysquant/fitting_dates.py)",
     "実装のコードで確かめた(<venvs>/item_1/_dl/c3)"),
    (98, "mihircoding/limitOrderBook", "run", "opp_mihircoding_lob",
     "価格・時間優先の照合の板・遅延の模擬(種つき)・ゼロ知能の注文流", "実装のコードで確かめた(<venvs>/item_2/src/c98)"),
    (95, "sacha9214/polymarket-fill-model", "run", "opp_polymarket_fill",
     "Polymarket の指値の待ち行列の模型。約定ごとに 60・300・1800 秒の markout を (capture, dérive) で返す(SCAN 5271・5277 行)",
     "実装のコードで確かめた(<venvs>/item_2/src/c95/fillmodel.py)"),
    (16, "Luczinsritter/event_driven_backtesting_engine", "run", "opp_luczinsritter",
     "yfinance の足の上の小さな事象駆動のバックテストと取引の分析(最大ドローダウン・Sharpe・Sortino・Kelly、SCAN 844 行)",
     "実装のコードで確かめた(<venvs>/item_3/_dl/c16)"),
    (48, "BacktestingMax", "none", None,
     "登録の要る閉じたサービス。チャートを 1 本ずつ再生し記録を残す(SCAN 5773 行)。料金の頁の機能の名に「Trailing drawdown, daily loss limits」「Trade Journal」(SCAN 5698 行)",
     "(a) の書き写しと (b) の公開の頁だけ(コードは公開されていない)"),
    (75, "Freqtrade", "run", "opp_freqtrade",
     "足の戦略の bot とバックテスト。バックテストの実行 ID は設定と戦略のファイルの sha1(optimize/backtest_caching.py)、最大ドローダウン、決済理由ごとの集計",
     "実装のコードで確かめた(<venvs>/item_3/freqtrade/…/freqtrade)"),
    (19, "Jesse", "none", None,
     "暗号資産の枠組み。バックテストは PostgreSQL と Redis が要る(SCAN 805 行)。実弾・ペーパーは license が要る(SCAN 1198 行)",
     "(a) の書き写しだけ(道具台帳 §3 の 11 件。導入も一次資料の読みもしない)"),
    (8, "OpenTrader", "none", None,
     "TypeScript の bot の枠組み。バックテストは足を順に流し、報告は注文の表と合計の損益(packages/backtesting/src/backtesting-report.ts 24-75 行)",
     f"実装のコードで確かめた(一次資料 {URL8} を読むだけの複製 <read>/OpenTrader。導入は §6-1 の検査で止めた = 項目 0 の RUNNABILITY.tsv 候補 8)"),
    (12, "pybotters", "run", "opp_pybotters",
     "取引所の HTTP / WebSocket の接続と DataStore", "実装のコードで確かめた(<venvs>/item_0/pybotters/…/pybotters)"),
    (88, "TradeSight", "repro", "opp_repro_88",
     "株のペーパー売買の枠組み(RSI / MACD の信号、戦略の対戦、Flask の画面)。walk-forward は重ならない塊の中の割合、再抽出は iid",
     f"実装のコードで確かめた(一次資料 {URL88} を読むだけの複製 <read>/tradesight)"),
    (91, "braedonsaunders/homerun", "run", "opp_homerun",
     "予測市場の bot。backend/services/backtest に等幅の walk-forward・定常ブロック・ブートストラップ・DSR・時間窓の CPCV・最大ドローダウン",
     "実装のコードで確かめた(<venvs>/item_2/src/c91/backend/services/backtest)"),
    (103, "IsaacCheng9/order-book-simulator", "run", "opp_isaaccheng_obsim",
     "注文の板の模擬器(照合・配信・Streamlit の画面)", "実装のコードで確かめた(<venvs>/item_2/src/c103)"),
]

# the lines of each reproduction per viewpoint (for 「再現した」)
REPRO_LINES = {
    ("opp_repro_15", "C3-1"): "walkforward/src/window.rs L14-L48(generate_windows)と runner.rs L280-L298(日付の半開区間で行を選ぶ)。"
                              "窓ごとの評価 runner.rs L357-L376 は定数を返す「Placeholder」で形 4 なので再現しない(a1-wf-fit-eval は結果なし)",
    ("opp_repro_15", "C3-2"): "walkforward/src/lib.rs L532-L557・L559-L610・L629-L645(組合せ・折り目と purge・組の学習の行)と L206-L216(組合せの数)",
    ("opp_repro_15", "C3-5"): "walkforward/src/lib.rs L612-L700・L715-L760(CPCV の各組の評価と PBO)、metrics/src/significance.rs L135-L333(述べた Sharpe の DSR)、"
                              "metrics/src/performance.rs L226-L266・L306-L355(系列の DSR)",
    ("opp_repro_15", "C3-13"): "backtest/src/collectors.rs L419-L423(約定率 = 約定した注文 / 出した注文)。取り逃しの数は結果に残さない(L519-L522)",
    ("opp_repro_15", "C3-14"): "metrics/src/risk.rs L12-L34(最大ドローダウンの割合)",
    ("opp_repro_88", "C3-14"): "src/strategy_lab/backtest.py L74-L81・L149-L164・L467-L468(実行中の最大ドローダウン、% )",
}

# candidates neither installed nor reproduced: viewpoint -> (judgement, reason); "*" = every viewpoint
NOT_RUN = {
    19: {"*": ("再現できない", "危険(道具台帳 §3 の 11 件 = 委任文 §4。導入も一次資料の読みもしない)。(a) の書き写し(SCAN 486・788-805・1198 行)は"
                               "導入・危険の検査・料金の記載で、この観点の機構の記載が無い。(b) は禁止")},
    48: {"*": ("再現できない", "(a) の書き写し(SCAN 5697-5775 行)は料金の頁の機能の名の一覧だけで、式・欄の定義が無い。(b) 公開の頁 https://www.backtestingmax.com/"
                               "(2026-09-25 GET 200、読むだけ)はチャートの再生・プロップファームの模擬・記録の紹介で、式もコードも公開されていない"
                               "(登録の要る閉じたサービス = SCAN 4335 行)。材料が足りず再現できない")},
}
# OpenTrader (8): read in full ((b)); the grep keys of opponents/SEARCH.tsv per viewpoint and what the hits are
VP_KEYS = {
    "C3-1": ["calendar_split", "walk_forward"], "C3-2": ["purged_split", "cpcv"], "C3-3": ["block_bootstrap"],
    "C3-4": ["mde"], "C3-5": ["dsr", "pbo"], "C3-6": ["iter_ledger", "sealed_read"], "C3-7": ["run"], "C3-8": ["run"],
    "C3-9": ["auto_repro"], "C3-10": ["prereg"], "C3-11": ["trade_metrics"], "C3-12": ["trade_metrics"],
    "C3-13": ["fill_metrics", "markout"], "C3-14": ["cost_breakdown", "exit_reasons", "drawdown"], "C3-15": ["purpose"],
    "C3-16": ["dashboard"], "C3-17": ["dashboard", "cdn"], "C3-18": ["dashboard"], "C3-19": ["dashboard"],
}
HITS_8 = {
    "block_bootstrap": "当たりは bot の起動の処理(packages/bot/src/platform.ts・app.ts)",
    "cost_breakdown": "当たりはバックテストの取引所の手数料が 0 の固定(packages/backtesting/src/exchange/memory-exchange.ts 68・151-152 行)",
    "purpose": "当たりは取引所の口座の種類 Paper(packages/types/src/common/enums.ts 30 行)で、指標の書き出しの目的の欄ではない",
}


def _tsv(target):
    p = RES / f"{target}.tsv"
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _search():
    with open(HERE / "opponents" / "SEARCH.tsv", encoding="utf-8") as fh:
        return {(r["target"], r["op"]): r for r in csv.DictReader(fh, delimiter="\t")}


def _reasons(rs, cap=900):
    """The distinct reasons the viewpoint's scenes ended with (the adapter's words), in scene order."""
    if not rs:
        return "表が無い"
    seen, out = set(), []
    for r in rs:
        d = r["detail_1"].replace("|", "/").removeprefix("adapter: ")
        if d not in seen:
            seen.add(d)
            out.append(f"{r['scene']}: {d}")
    t = " / ".join(out)
    return t if len(t) <= cap else t[:cap] + "…(全文は survey_results の表)"


def main() -> int:
    search = _search()
    vps = list(S.VIEWPOINTS)
    ids = {vp: [s["id"] for s in S.SCENES if s["viewpoint"] == vp] for vp in vps}
    lines = [
        "# 項目 3「検証・再現・出力」— 動かせなかった候補の検討表",
        "",
        "場面係が書く(委任文 §3「動かせない候補の検討と再現」・場面集の規則 6・9)。この表は `tests/bt/battery/item_3/gen_considered.py` が作る。",
        "",
        "- 候補 = REQUIREMENTS.md §3.3 が名を挙げた 16 件(15・107・0 mlflow・3・98・95・16・48・75・19・8・12・88・91・103)。**番号 0 は台帳に番号の無い"
        " mlflow の印**(REQUIREMENTS.md §3.3「候補番号なし」。台帳の 0 番ではない)。§3.3 が C3-16 で「区分1 の対象候補としては 0 件」と書いた"
        " 88・91・103 も、名が挙がっているので候補に入れた。",
        "- 「動かせた候補」= 隔離した venv で動き、その観点の場面で「結果なし」以外を 1 つ以上返した候補(survey_results/opp_*.tsv から機械で数えた)。"
        "導入はできたがその観点の場面を 1 つも取れなかった候補は、その観点では表の行に載せる(規則 4 の「候補ごとの欠け」)。",
        "- 段: どの観点にも無い(REQUIREMENTS.md §3.0・§3.4。`段(機構)`・`段(既定)` は約定の模型の観点だけの列)。だから「段が低い」を理由にしたスキップは無い。"
        "調査報告(SCAN)は多くの候補について機能の一行の説明しか持たず、「上位互換」を 1 能力ずつ調査報告の行で示せないので、上位互換のスキップも無い。",
        "- 「再現した」の候補(15・88)は一次資料を読むだけで複製し(実行しない)、場面に掛かる機構を注釈に行を 1 対 1 で書き写した(opponents/repro_*.py)。"
        "再現も場面集の全部の場面に通した(survey_results/opp_repro_*.tsv)。",
        "- 実装の列の <venvs> は `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs`、<read> は同じ scratchpad の "
        "`bt/i3_r1_scenekeeper/read`(読むだけの複製と取得の記録 i3_r1_scenekeeper_read.log)、「…」は `lib/python3.11/site-packages`。",
        "",
    ]
    for vp in vps:
        runnable, rows = [], []
        for num, name, kind, target, mech, impl in CANDS:
            tag = f"{num} {name}"
            if kind == "run":
                rs = [r for r in (_tsv(target) or []) if r["viewpoint"] == vp]
                ok = [r for r in rs if r["class_1"] != "結果なし" or r["class_2"] != "結果なし"]
                if ok:
                    runnable.append(tag)
                    continue
                first = _reasons(rs)
                rows.append((tag, mech, impl, "持たないと確認した",
                             f"場面が測る「{S.VIEWPOINTS[vp]}」の口が無い: {first}。`run_battery.py --target {target}` の出力 "
                             f"survey_results/{target}.tsv の {'・'.join(ids[vp])} の行が全部「結果なし」"))
            elif kind == "repro":
                rs = [r for r in (_tsv(target) or []) if r["viewpoint"] == vp]
                ok = [r for r in rs if r["class_1"] != "結果なし" or r["class_2"] != "結果なし"]
                fname = "opponents/repro_15_backtestingcore.py" if num == 15 else "opponents/repro_88_tradesight.py"
                if ok:
                    rows.append((tag, mech, impl, "再現した",
                                 f"{fname} に一次資料の {REPRO_LINES.get((target, vp), '(行は再現の注釈)')} を書き写した(注釈に行を 1 対 1)。"
                                 f"場面の結果は survey_results/{target}.tsv の {'・'.join(r['scene'] for r in ok)} の行"))
                else:
                    first = _reasons(rs)
                    rows.append((tag, mech, impl, "持たないと確認した",
                                 f"一次資料を読んだ結果、場面が測る「{S.VIEWPOINTS[vp]}」の口が無い: {first}(再現 {fname} を場面に通した"
                                 f" survey_results/{target}.tsv の {'・'.join(ids[vp])} の行が全部「結果なし」)"))
            elif num == 8:
                parts = []
                for k in VP_KEYS[vp]:
                    r = search.get(("read_8", k))
                    n = r["n_files"] if r else "-"
                    parts.append(f"grep -rliE '{r['regex'] if r else k}' → {n} ファイル" + (f"({HITS_8[k]})" if k in HITS_8 and n not in ("0", "-") else ""))
                rows.append((tag, mech, impl, "持たないと確認した",
                             f"一次資料 {URL8} を読んだ: " + "、".join(parts) + "。バックテストの報告は注文の表・取引の数・合計の損益だけ"
                             "(packages/backtesting/src/backtesting-report.ts 24-75 行)で、この観点の口が無い"))
            else:
                j, why = NOT_RUN[num].get(vp) or NOT_RUN[num]["*"]
                rows.append((tag, mech, impl, j, why))
        lines.append(f"### 観点 {vp} {S.VIEWPOINTS[vp]}")
        lines.append("")
        lines.append(f"動かせた候補: {len(runnable)} 件" + (f"({', '.join(runnable)})" if runnable else ""))
        lines.append("")
        lines.append("| 候補 | 機構 | 実装 | 判断 | 理由 |")
        lines.append("|---|---|---|---|---|")
        for r in rows:
            lines.append("| " + " | ".join(str(x).replace("\n", " ") for x in r) + " |")
        lines.append("")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{OUT}: {len(vps)} viewpoints")
    return 0


if __name__ == "__main__":
    sys.exit(main())
