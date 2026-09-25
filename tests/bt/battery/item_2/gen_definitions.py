#!/usr/bin/env python3
"""Generate DEFINITIONS.md of the item 2 battery from i2_scenes.py.

    python3 tests/bt/battery/item_2/gen_definitions.py          # write
    python3 tests/bt/battery/item_2/gen_definitions.py --check  # exit 1 if DEFINITIONS.md is stale

Every expected answer printed here is computed by the scene's oracle (never typed).  The section that
starts at REVIEW_MARK (the scene-keeper's pre-submission review, prose) is kept as it is.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import i2_scenes as S  # noqa: E402

OUT = HERE / "DEFINITIONS.md"
REVIEW_MARK = "## 提出前の吟味"
VIEWPOINTS = {
    "C2-1": "発注の型", "C2-2": "取消と訂正・部分約定", "C2-3": "取引所固有の規則", "C2-4": "異常系の注入",
    "C2-5": "約定/待ち行列の段", "C2-6": "列の位置の追跡・先行注文の取り消しの扱い", "C2-7": "板を辿る成行・市場影響の関数",
    "C2-8": "楽観側・悲観側の幅", "C2-9": "遅延の模型", "C2-10": "費用(既定値なし)", "C2-11": "口座と会計",
    "C2-12": "JPX データ待ちの扱い",
}

HEAD = """# 項目 2 の場面集 — 定義(執行の模型: 注文・約定・遅延・費用・口座)

**この文書は `gen_definitions.py` が `i2_scenes.py` から作る。手で直さない**(末尾の「提出前の吟味」の節だけは場面係の文で、生成器はそのまま残す)。
期待の値は全部、場面ごとの正解の関数(エンジンを見ない閉じた式)が場面の入力から計算したもので、手で打った数は無い。
固定した要件: `docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/REQUIREMENTS.md` の観点 C2-1〜C2-12。

## 0. 読み方

- **値の場面** = その値が正しいか(合成の入力と、閉じた式で出した正解)。**能力の場面** = X ができるかを、X を使ったときに出るはずの観測できる結果(正解)で見る。どちらも、対象を実際に呼んだ結果を正解と突き合わせる(場面集の規則 1)。「持っている」という申告は数えない。
- **対になった場面**(「変形」の欄がある場面): 対照の入力で正解と一致し、**かつ**変形の入力を断ったときだけ「正解と一致」。変形で単一の結果を返したら「不一致」。対照が正解と合わなければ、その不一致をそのまま記録する。
- **正しさ**の分類(良い順。場面集の規則 5): 正解と一致 > 対応なし(対象が明示的に拒否した・例外を出した)> 不一致(黙って違う値を返した)> 結果なし(その場面を対象に渡せなかった。何を試したかを注記に書く)。
- **再現**: 同じ場面を別々の process で 2 回走らせ、正しさの分類と観測(出力の全体の正規化した JSON の sha256)が同じなら「2 回の実行で同じ」。
- 時刻は UTC の int64 ナノ秒。T0 = 2026-01-05 00:00:00 UTC。「T0+5ms」は T0 から 5 ミリ秒後。JST は UTC+9。

## 1. 入力の形(全場面で同じ)

| 鍵 | 意味 |
|---|---|
| product | 商品: symbol・venue・tick(呼値)・min_qty(最小数量)・qty_step・quote_ccy(値の通貨)・margin(証拠金取引か) |
| rules | 取引所の規則の宣言(例: off_tick = reject / round_passive、post_only = reject_if_crossing、market_remainder = cancel、self_trade = cancel_taker、sessions_jst、price_limit、closed_utc_ns、outside_session = queue_to_next_open、amend_qty_down = keep_priority、mark = last_trade、market_ref = last_trade) |
| market | 市場の事象の列(時刻順。同じ時刻は列の順): book(板の写真: bids・asks = [値, 量] の良い順。当方の注文は含まない外部の板)/ trade(約定: px・qty・aggressor)/ bar(足: t = 足の終わり、span_ns、o・h・l・c・v)/ funding(資金調達: rate・mark)/ rollover(FX の日替わり)/ corporate(分割・併合: ratio)/ fx_rate(為替)/ l3_add・l3_cancel(注文ごとの板の出入り) |
| actions | 戦略の行為の列(時刻 = 戦略が出した時刻): place(ref・side・type = market / limit / stop・qty・px・stop_px・tif = GTC / IOC / FOK・post_only・reduce_only・oco = 相手の ref)/ cancel(ref)/ amend(ref・px・qty)/ kill(Kill Switch) |
| fill_model | 約定の模型の宣言: tier(道具台帳 §2.1 の段 0〜6)・cancel_stance(先行注文の取り消しの扱い)・impact(市場影響の関数)・range(楽観側 optimistic と悲観側 pessimistic の 2 つの模型)。null = 場面が模型を問わない(どの段でも正解が同じになるように作ってある) |
| latency | 遅延の宣言: feed(配信)・order(発注)・cancel(取消)・notice(受付・拒否の知らせ)の 4 つを別々に。kind = constant(ns)/ empirical(samples_ns と seed) |
| costs | 費用の宣言: maker_rate・taker_rate(負 = 払い戻し)・spread・funding・swap・fee_table と、出所の欄 source。**費用を測らない場面も 0 と出所を明示する**(既定値を持たない、の場面と矛盾しないため) |
| account | 口座: currency・cash・leverage・maint_ratio・liquidation_price・source |
| inject | 異常系の注入: kind = reject / timeout / unknown と ref |
| checkpoints | 途中の時点の名前 → 時刻(累計の約定量を見る) |
| end_t | 場面の終わりの時刻 |

**市場の事象の整合(全場面に同じ規則)**: 約定が、表示中の最良の気配より悪い値で出るとき(売りの約定が最良の買いより下、買いの約定が最良の売りより上)は、同じ時刻の約定の直前に、その値より良い側の値位を除いた板の写真を置く(`i2_scenes.consistent`)。板を実際に照合する対象でも、約定の列だけを見る対象でも、同じ市場として読めるようにするため。気配の内側の値の約定(例: 外部の買い 9999 / 売り 10001 のときの 10000)は、外部の板に表示されない量の約定か、当方の注文(外部の板には含めない)に当たった約定として読む(例: c2-5 の段の場面の 9994 は、当方の 9995 の買いを跨いで出た約定)。

## 2. 期待の鍵(観測から同じ手順で導く。どの対象も同じコードで読む)

| 鍵 | 意味 |
|---|---|
| status.<ref> | 注文の終わりの状態(filled / open / canceled / rejected / state_unknown) |
| filled.<ref> | 約定量の合計 |
| avg_px.<ref> | 約定量で重みを付けた平均の約定値 |
| first_fill_t.<ref> | 最初の約定の取引所の時刻 |
| cum.<ref>@<点> | その時点までの累計の約定量 |
| fee.<ref> | 約定ごとの手数料の合計(払い。払い戻しは負) |
| lat_in.<ref> | 最初の約定の時刻 − 出した時刻 |
| sent.<ref> | 取引所に届いた発注の回数 |
| notice.<ref>.<種類> | 戦略がその知らせを見た時刻(ack / reject / fill / cancel、terminal = reject と cancel の早い方) |
| seen.<印> | 印の付いた市場の事象を戦略が見た時刻 |
| account.<欄> | 場面の終わりの口座の値(position・realized・unrealized・avg_px・exposure_ns・liquidated_t・realized_jpy) |
| costs.<欄> | 場面の間に払った資金調達・スワップ(受け取りは負) |
| range.<側>.<鍵> | 楽観側・悲観側それぞれの同じ鍵 |

値の比べ方: 文字列と整数は完全一致、小数は絶対・相対とも 1e-9 以内。`ge v` は v 以上、`in [..]` はどれかと一致。

## 3. 対象の走らせ方

`python3 tests/bt/battery/item_2/run_battery.py --target <対象> --out <出力.tsv>`。全場面を、場面ごとに対象の interpreter の別の process で 2 回走らせ、2 回の一致を再現の欄に書く。対象の一覧は `--list-targets`。
新実装の adapter(`adapters/new_impl.py`)は口だけを決めてある(本体は資料係が毎周、新実装の公開の口だけを呼んで書く): `TARGET.run(場面の入力) -> 観測`。エンジンが全体を断ったら `Refused`、注文 1 つを断ったらその注文を rejected と記録して続ける、場面を渡す公開の口が無ければ `NotExpressible(試したこと)`。正解の関数・期待の値・場面の id を読まない。
"""


def _fmt(v):
    if isinstance(v, dict) and "op" in v:
        return f"{v['op']} {json.dumps(v['v'], ensure_ascii=False)}"
    if isinstance(v, float):
        return repr(round(v, 12))
    return json.dumps(v, ensure_ascii=False)


def _input_json(inp):
    return json.dumps(inp, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def body() -> str:
    out = [HEAD]
    out.append("## 4. 場面(観点ごと)\n")
    for vp, title in VIEWPOINTS.items():
        sc = [s for s in S.SCENES if s["viewpoint"] == vp]
        nv = sum(1 for s in sc if s["kind"] == "値")
        out.append(f"### {vp} {title}(場面 {len(sc)}: 値 {nv}・能力 {len(sc) - nv})\n")
        nouns = S.NOUNS.get(vp, {})
        if nouns:
            out.append("要件の語 → 場面: " + " / ".join(f"{k} → {', '.join(v)}" for k, v in nouns.items()) + "\n")
        for s in sc:
            exp = S.expected(s)
            out.append(f"#### {s['id']}({s['kind']}の場面)— {s['title']}\n")
            out.append(f"- **何を測るか**: {s['measures']}")
            out.append(f"- **入力(言葉で)**: {s['derivation']}")
            out.append("- **期待(正解の関数が入力から計算した値)**: " + " / ".join(f"`{k}` = {_fmt(v)}" for k, v in exp.items()))
            if "variant" in s:
                out.append("- **変形**: 対照の入力との違い = " + _diff(s["input"], s["variant"]) + "。変形は断るのが正解。")
            out.append(f"- **入力(全文)**: `{_input_json(s['input'])}`")
            if "variant" in s:
                out.append(f"- **変形の入力(全文)**: `{_input_json(s['variant'])}`")
            out.append("")
    out.append("## 5. 場面にしなかった要件の語(理由つき。批評家が見る)\n")
    out.append("| 観点 | 語 | 理由 |\n|---|---|---|")
    for vp, items in S.NOT_SCENES.items():
        for noun, why in items:
            out.append(f"| {vp} | {noun} | {why} |")
    out.append("")
    return "\n".join(out)


def _diff(a, b, path=""):
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in b:
                diffs.append(f"{path}{k} を欠く")
            elif k not in a:
                diffs.append(f"{path}{k} を足す")
            elif a[k] != b[k]:
                sub = _diff(a[k], b[k], f"{path}{k}.")
                diffs.append(sub)
    else:
        diffs.append(f"{path.rstrip('.')} が {json.dumps(b, ensure_ascii=False)[:120]}")
    return "・".join(d for d in diffs if d)


def render(old: str) -> str:
    review = old[old.index(REVIEW_MARK):] if REVIEW_MARK in old else f"{REVIEW_MARK}\n\n(未記入)\n"
    return body() + "\n" + review


def main() -> int:
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    new = render(old)
    if "--check" in sys.argv:
        if new != old:
            print("DEFINITIONS.md is stale: run gen_definitions.py")
            return 1
        print("DEFINITIONS.md is up to date")
        return 0
    OUT.write_text(new, encoding="utf-8")
    print(f"wrote {OUT} ({len(S.SCENES)} scenes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
