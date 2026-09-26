#!/usr/bin/env python3
"""Write tests/bt/battery/item_1/DEFINITIONS.md from i1_scenes.py (the scene list,
inputs, expected answers and how they were fixed) plus the fixed prose below.

    python3 tests/bt/battery/item_1/gen_definitions.py          # write
    python3 tests/bt/battery/item_1/gen_definitions.py --check  # exit 1 if the file differs
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import i1_scenes as S  # noqa: E402

HEAD = """# 項目 1「データと時刻」— 場面集の定義

場面係が作り、作業者の 1 周目の前に固定する(委任文 §3「場面集」「場面集の規則」1〜9)。固定した要件は
`docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/REQUIREMENTS.md`(観点 V1〜V7)。この文書の「場面」の節は
`gen_definitions.py` が `i1_scenes.py` から書く(場面の中身と文書が食い違わないため。手で直さない)。

## 1. 場面の 2 種類

- **値の場面**: 合成の入力と、エンジンを見ずに決めた正解(手計算・閉じた式・定義どおりの素朴な数え)で、その値が正しいかを見る。
  正解の出し方は場面ごとの「正解の出し方」に書く。
- **能力の場面**: X ができるかを、X を使ったときに出るはずの結果(正解)で見る(規則 1)。「持っている」という申告・型や名前の有無は数えない。
- どの観点にも値の場面を 1 つ以上置く(規則 3)。場面は振る舞いを見て、作りの形を見ない(規則 2)。

## 2. 入力の形(adapter が受け取るもの)

`op` で 3 つに分かれる。runner は場面ごと・実行ごとに新しいフォルダ(`root`)を作り、`files` をそこに書き、`root` を足して渡す。

- `op = "load"`(V1〜V5): `files`(`path` = root からの相対パス、`text`、`gzip`(mtime 0 で圧縮)、または `symlink_to`)、
  `datasets`(`name`・`paths`(1 つのデータを成すファイル。2 本なら世代)・`spec`・任意の `range_ns` = [始まり, 終わり) の読む範囲)、
  `want`(`events` = 全部の欄 / `times` = 時刻の欄だけを判定 / `anomalies` / `hashes`)。
  `spec` = データの宣言: `format`(csv / jsonl = 1 行 1 つの JSON。jsonl の列の名は入れ子を . でつないだ道 = 例 raw.o.T)・`header`(見出しの有無。無ければ `names`)・`delimiter`・`compression`・
  `kind`(trade / quote / bar / book / funding / liquidation。book の `fields` は段ごとの列の名の列と `levels`)・`symbol`・`asset`・`time`(`columns` = 時刻の列(2 列なら `join` で合わせる)、
  `unit` = s / ms / us / ns / iso、`tz` = オフセットの無い時刻の時間帯)・`fields`(共通の欄 → 列の名)・`side_map`(列の値 → buy / sell / "")・
  `bar`(`interval_s`・`label` = 足の時刻は始まり・`session` = 24x7)・`key`(重複と食い違いのキー。id または足の始まり)。
- `op = "jpx"`(V6): `bars`(code・date・open・high・low・close・volume の日足)・`actions`(split / reverse_split の `ratio` と `ex_date`、
  code_change の `new_code` と `ex_date`)・`listings`(code・listed・delisted = 上場でなくなる最初の日、無しは null)・`as_of`・`universe_dates`。
- `op = "vector_vs_event"`(V7): `trades`(t_ns・px・qty・side・id)または `bars`(start_ns・OHLCV)・`interval_s`・`rule`・`want`。

adapter の決まり(`i1_protocol.py`): ファイルはパスで対象に渡し、spec を対象の公開の選択肢に置き換える。adapter はデータのファイルを
自分で開かない・解釈しない・書き換えない。対象が出さなかった値を計算しない。正解を読まない。場面の id で分けない。
構造化された入力(V6・V7)は、対象の API が取る入れ物(DataFrame・対象の事象の型)に入れ替えてよい(入れ物の変更で、計算ではない)。

## 3. 観測の形と判定の決まり(`i1_judge.py`)

記録: 約定 = t_ns・px・qty・side・id(文字列)/ 気配 = t_ns・bid・ask・bid_qty・ask_qty / 足 = start_ns・open・high・low・close・volume /
板の写真 = t_ns・bids・asks(良い段から [値段, 数量] の列。空欄の段は載せない)/ 資金調達 = t_ns・rate / 清算 = t_ns・px・qty・side。
時刻の欄は int(ナノ秒、UTC)でなければならない(float の時刻は不一致)。

- `events`: データごとに、同じ件数・同じ順で、正解の記録が名指す欄が全部一致する(整数と文字列は完全一致、浮動小数は完全一致。場面が `tol` を持てば相対の差 ≤ tol)。
- `anomalies`: データごとに (種類, 時刻) の多重集合が一致する。種類と時刻の定義:
  - `duplicate` = spec の `key` が同じで、全部の列が同じ行(時刻 = その行の時刻)。
  - `conflict` = `key` が同じで、値が違う行(時刻 = その行の時刻)。
  - `backward` = その行の時刻 < それより前の行の時刻の最大(時刻 = その行の時刻)。
  - `gap` = 足の間隔の格子で、最初の足と最後の足の間に行の無い始まりの時刻 1 つにつき 1 件(24x7)。
  異常の種類の一部しか持たない対象は、持つ種類の結果をそのまま返す(持たない種類を黙って見落とすと不一致になる =「黙って結合しない」)。
  異常を報せる口が全く無い対象は `anomalies` を返さない(= 不一致。口が無いことを adapter が名指せば「結果なし」)。
- `hashes`: 正解の全部のパスについて、ディスクに書いたバイト列(gzip は圧縮したままのバイト列)の sha256 が一致する。
- `adjusted`: 銘柄の集合が一致し、銘柄ごとに `events` と同じ決まり。`universe`: 日付ごとに銘柄の集合が一致する。
- `paths`: 事象駆動(`event`)と近道(`vector`)の両方が正解の全部の欄を持ち、それぞれが正解と一致し、**2 つの経路がビット単位で一致する**。
- `speed`: 名指す欄で 2 つの経路がビット単位で一致し、`timing.vector_s < timing.event_s`(adapter が両経路の呼び出しの前後で測った壁時計の秒)。
- 変形(`variant`)を持つ場面(V5): 対照が正解と一致し、かつ変形を対象が拒んだときだけ「正解と一致」。変形を拒まずに読めば「不一致」。

表のセル(資料係が作る): **正しさ** = 正解と一致 / 対応なし(対象が明示的に拒んだ・例外を出した)/ 不一致(黙って違う値を返した)/ 結果なし(走らせられず、結果が 1 つも無い。理由を注記に書く)。
**再現** = 2 回の実行で同じ(正しさの分類と観測の要約(時刻の秒を除く)が 2 回とも同じ)/ 2 回で違う(値)/ 結果なし。
runner は同じ場面を別のプロセスで 2 回走らせ、両方を記録する。

**「最も良い結果」の順**(規則 5): 正解と一致 > 対応なし > 不一致 > 結果なし。正しさが同じなら、2 回の実行で同じ を上に置く。

## 4. V7 の規則

- 足の作り方: 足 = [始まり, 始まり + interval) の約定。始値 = 最初、高値 = 最大、安値 = 最小、終値 = 最後、出来高 = 数量の和。約定の無い区間は足を作らない。
- 規則 `sma_long_flat`(n, init_cash, unit): sma_t = 直近 n 本の終値の平均(n 本に満たない足は無し = null)。
  position_t = unit(終値_t > sma_t のとき)/ 0。position_t は足 t の終値で決まり、足 t+1 の間持つ。費用なし。
  equity_t = init_cash + Σ_{s ≤ t} position_{s-1} × (終値_s − 終値_{s-1})。
- 規則(戦略)は adapter が対象の事象駆動の API と近道の API の上に書く(規則は戦略で、どの対象でも利用者の符号)。

## 5. 対象(表の行になるもの)

- 新実装 = `adapters/new_impl.py`(**口だけ**。本体は資料係が毎周、新実装の公開の API だけを呼んで書く)。
- 調査結果の側 = 要件のファイル §3 が名を挙げた候補のうち、隔離した venv で動いたものと、動かせない候補の再現(`opponents/`。一覧は `i1_targets.py`、
  導入の記録は `opponents/RUNNABILITY.tsv`、動かせない候補の検討は `opponents/CONSIDERED.md`)。場面ごとに、動いた対象のうち最も良い結果を 1 行に寄せる。
- 試金石 = `mutant.py`(新実装を包み、1 か所だけ誤らせる。何を誤らせたかは `mutant.py` の MUTANT)。

## 6. 場面にしていない・射程の外

- 要件のファイル §2 の射程外(執行の模型・検証の統計・実行記録の形そのもの)はこの場面集で測らない。V4 は「読んだファイルの sha256 を対象が記録して返すか」を見る(記録の置き場の形は項目 3)。
- 実データは使わない(全部合成)。JPX 個別株の分割・併合・上場廃止・コード変更は合成のデータだけで測る(この環境で JPX 個別株の調整の実データを探した方法と結果は要件のファイル §4)。
- V7 の速さは壁時計の比べなので、2 回の実行で分類が変わりうる(変われば「2 回で違う」と記録する)。
"""


def _short(obj, limit=900):
    s = json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= limit else s[:limit] + f" …(全 {len(s)} 字。全文は i1_scenes.py の場面の定義)"


def _input_md(inp: dict) -> list[str]:
    out = []
    if inp["op"] == "load":
        for f in inp["files"]:
            if "symlink_to" in f:
                out.append(f"  - `{f['path']}` → symlink `{f['symlink_to']}`")
                continue
            head = f["text"].splitlines()
            out.append(f"  - `{f['path']}`" + ("(gzip)" if f.get("gzip") else "") + f"({len(head)} 行):")
            out.append("    ```")
            out += ["    " + ln.replace("\t", "<TAB>") for ln in head[:8]]
            if len(head) > 8:
                out.append(f"    …(残り {len(head) - 8} 行)")
            out.append("    ```")
        for d in inp["datasets"]:
            extra = f"、range_ns = {d['range_ns']}" if "range_ns" in d else ""
            out.append(f"  - データ `{d['name']}`: paths = {d['paths']}{extra}、spec = `{json.dumps(d['spec'], ensure_ascii=False)}`")
        out.append(f"  - want = {inp['want']}")
    elif inp["op"] == "jpx":
        out.append(f"  - bars = `{_short(inp['bars'], 700)}`")
        out.append(f"  - actions = `{json.dumps(inp['actions'], ensure_ascii=False)}`、listings = `{json.dumps(inp['listings'], ensure_ascii=False)}`")
        out.append(f"  - as_of = {inp['as_of']}、universe_dates = {inp['universe_dates']}")
    else:
        for k in ("trades", "bars"):
            if k in inp:
                out.append(f"  - {k}({len(inp[k])} 件)= `{_short(inp[k][:12], 700)}`" + (" …" if len(inp[k]) > 12 else ""))
        out.append(f"  - interval_s = {inp['interval_s']}、rule = `{json.dumps(inp['rule'], ensure_ascii=False)}`、want = {inp['want']}")
    return out


REVIEW = """## 8. 返す前の吟味(場面係の最初の作り。委任文 §3「提出前の吟味」、L-433)

固定した要件(REQUIREMENTS.md の V1〜V7)・場面集の規則 1〜9・比較の観点を読み直し、「非常に厳しい監査役・批評家なら何を [止める] にするか」を
観点ごとに列べ、返す前に潰した(潰せなかったものは「残り」に書く)。

| 観点・規則 | 止められうること | 潰した方法(ファイル・試験) |
|---|---|---|
| V1 | 「§1 の全資産」なのに約定と足だけ | bitFlyer の約定(REST・統合版 gzip)・Binance aggTrades(見出しなし)・FX のイベントティック・JPX の 1 分足(2 列・日本時間)・板の上位 10 段(空欄の段)・資金調達・清算(JSON 1 行 1 通・入れ子の欄)の 8 形を値の場面にし、1 回の呼び出しで全部の場面を足した(`v1-*`) |
| V1 | 「資産ごとに専用のパーサを書かない」を形で見ている(規則 2 違反) | 形ではなく振る舞いで見る: 種から列の名・並び・区切り・見出し・単位を引いた 5 ファイルを宣言だけで読ませる(`v1-generic-shape`)。専用の読み口を場面の形に合わせて書いた対象は通らない |
| V2 | 単位の変換を整数の秒だけで見ている | 小数部つきの 10 進(秒 9 桁・ミリ 6 桁・マイクロ 3 桁)とナノ秒の整数と 9 桁の ISO で同じ瞬間を書き、浮動小数に落とすと崩れる形にした。オフセット 6 通り・宣言した時間帯・日付の境・2 列の時刻(`v2-*`)。正解は試験で Fraction と数字の正規表現で読み直した(`test_v2_*`・`test_local_zone_*`) |
| V3 | 「件数が一致」だけで、何を 1 件と数えるかが無い | 種類ごとの定義(キー・全列・最大・格子)を §3 に書き、(種類, 時刻) の多重集合で比べる。同じ時刻で id の違う正当な行を対照に入れ、何でも異常と言う対象を通さない(`v3-clean-control`) |
| V3 | 一部の種類しか持たない相手を不当に「不一致」にしている | §3 に決まりとして書いた(持つ種類の結果をそのまま返す。持たない種類を黙って見落とすのが「黙って結合」)。要件の「黙って結合しない」をそのまま測るため |
| V4 | ハッシュを場面の側で計算して正解にしている(自己採点) | 正解は書いたバイト列そのものへの sha256(gzip は mtime 0 の圧縮後のバイト列)。1 バイト違い・同じ中身の別の場所も置いた(`v4-sha256-distinguishes`)。試験 `test_v4_expected_hash_is_of_the_written_bytes` |
| V5 | 拒むだけの対象(何でも拒む)が通る | どの場面も対照(許されるパスの同じ中身)を正しく読んだうえで変形を拒んだときだけ正解。名前に o3c を含むだけの生データは読む(`v5-reject-o3c`)。`..` と symlink で抜ける道(`v5-reject-dotdot`・`v5-reject-symlink`)、封印の境ちょうど(`v5-seal-boundary`)。変形の実体が拒むべき場所を指すことを試験で確かめた(`test_every_scene_materializes_*`) |
| V6 | 分割だけで、併合・コード変更・上場廃止・先読みが無い | 分割・併合・as_of が ex_date より前(先読みしない)・コード変更(系列と銘柄集合)・上場廃止と後の上場(銘柄集合)の 5 場面。値は割り切れる数で分数から出した(`test_v6_*`) |
| V7 | 「近道が事象駆動と一致」を丸めの出ない整数だけで見ている | 整数の場面に加え、10 進の小数の終値で経路の間のビット一致を求める場面(`v7-rule-fractional`)。正解は対象に渡す浮動小数の正確な値から分数で出した(最初の作りでは 10 進の文字列から出していて、際どい比べ(差 4.7e-15)で正解そのものが誤っていた。対象を走らせて見つけ、終値を選び直し、差が 0.033 以上であることを試験にした `test_v7_rule_on_the_exact_binary_values_and_no_near_tie`) |
| V7 | 速さを測っていない | 2 万本の足で両経路の秒を比べ、同時に値の正解とビットの一致も見る(`v7-speed`) |
| 規則 1 | 能力の場面が「動いた」で決まる | 能力の場面も全部、正解(結果)を持つ(`test_capability_scenes_are_judged_by_results_too`) |
| 規則 3 | 観点に値の場面が無い | 全観点に値の場面(`test_every_viewpoint_has_a_value_scene_*`)。最初の作りでは V5 に値の場面が無く、この試験で見つけて `v5-seal-boundary` を足した |
| 規則 4 | 動いた道具の一部の場面だけを走らせた | runner は対象ごとに全場面を 2 回ずつ別のプロセスで走らせる。動いた道具は全部、全場面に通した(記録は opponents/RUNNABILITY.tsv と survey_results/) |
| 規則 5 | 表の「最も良い結果」の順が無い | §3 に書いた |
| 規則 6・9 | 動かせない候補を検討せずに外した / 理由なしのスキップ | 13 候補 × 7 観点の全部を opponents/CONSIDERED.md に載せ、`scripts/check_bt_considered.py --write` で誤り 0 件。スキップは 0 件(段の無い観点なので「段が低い」は使えず、「上位互換」も使っていない)。機構を持つのに場面の形を取れない候補は、機構を導入済みのコードどおりに再現した |
| 規則 7 | 試験の置き場所 | 場面集の試験は tests/bt/battery/item_1/ だけ |
| 判定 | 判定器が甘い | 正解そのものは通り、1 ns のずれ・欄の欠け・時刻の float・id の int・1 ビット違いの経路・遅い近道・空欄の段を 0 で埋めた板・異常の 1 件の欠けを全部落とす(`test_judge_*`・`test_board_*`) |
| 試金石 | 不具合が場面に当たらない / 2 回で違う | 時間帯の宣言を無視する 1 か所だけ。当たる場面を mutant.py に名指しし、名指した場面だけが崩れることを試験にした(`test_mutant_breaks_exactly_the_scenes_it_names`)。決定的なので再現の欄は変わらない |
| adapter | adapter が値を作れば相手が強くも弱くもなる | adapter はファイルを開かない・正解を読まない(i1_protocol.py)。再現は「読み取りは再現の側の手段」と明記し、V3 の検査の機構にだけ使う(読み取りだけで V1・V2 の正解を取らないように、V3 以外の場面では結果を返さない) |

**残り(潰せなかったこと・未確認)**
- 調査結果の側の導入・再現の経緯(対象ごとの事情)は、審査員が読むこの文書には書かず、opponents/RUNNABILITY.tsv・opponents/attempts/・opponents/CONSIDERED.md に書いた(盲検のため)。
- 要件のファイル §3.4 の番号の並びの「5・7」と「その他」の読み方(CONSIDERED.md の冒頭)。
"""


def build() -> str:
    lines = [HEAD, "## 7. 場面(観点ごと)", ""]
    for vp, title in S.VIEWPOINTS.items():
        sc = [s for s in S.SCENES if s["viewpoint"] == vp]
        lines.append(f"### {vp} {title}({len(sc)} 場面: 値 {sum(s['kind'] == '値' for s in sc)}・能力 {sum(s['kind'] == '能力' for s in sc)})")
        lines.append("")
        for s in sc:
            lines.append(f"#### `{s['id']}`({s['kind']}の場面)")
            lines.append(f"- 何を測るか: {s['what']}")
            lines.append("- 入力:")
            lines += _input_md(s["input"])
            if "variant" in s:
                lines.append("- 変形(拒むべき入力):")
                lines += _input_md(s["variant"])
            exp = S.expected(s)
            lines.append(f"- 期待: `{_short(exp)}`" + (f"(浮動小数は相対 {s['tol']} まで)" if s.get("tol") else ""))
            lines.append(f"- 正解の出し方: {s['how']}")
            lines.append("")
    lines.append(REVIEW)
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    text = build()
    out = HERE / "DEFINITIONS.md"
    if "--check" in sys.argv:
        ok = out.exists() and out.read_text(encoding="utf-8") == text
        print("OK" if ok else "DEFINITIONS.md は i1_scenes.py から作ったものと違う(gen_definitions.py を回す)")
        return 0 if ok else 1
    out.write_text(text, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
