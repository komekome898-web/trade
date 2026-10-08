"""マチルダ(v37)の純な関数(引数の検め・建ての旗・決済の旗・利確の値段)の表。

単純な道の移し替え `src/bot/strategy/matilda_simple.py` がこの関数を import して使う。古い道の場面の試験は、古い道を
測りに使わなくなったので消した(L-854「**他のいらん試験も消せ**」)。

オーナーの逐語(表の出所):
- L-776「**全ての変数は固定値でなく調整可能な値で、それはバックテストで探る族の種類と同義です。modeの切り替えとかもあったと思う。**」
- L-782「**1. 利確は中央値から exit_setting × ボラ 離れたところ**」/ L-788「**breakexitsizeはロット数上限に合わせる**」/ L-789「**あってる**」
"""
from __future__ import annotations

import pytest

from bot.bt.road.strategy import RoadStrategyError
from bot.strategy import matilda_v37 as M

# 小さな窓の引数。原典の値は V37_ORIGINAL。
BASE = dict(levels=2, foot=1, vola_count=3, range_count=3, alert_count=1000, range_setting=None,
            over_range_setting=None, vola_setting=None, entry_setting=2.0, exit_setting=1.0, break_delay=0,
            break_dist=0.5, break_len_mult=2, beard_ignore=None, step_setting=1.0, step_exit=1.0, b_signal=False)


# ================================================================ U1 引数
def test_u1_param_keys_and_original_values():
    # 引数は全部で 17。原典の値(v37:109-160 と オーナーの決め L-782・L-784・L-788)。fukuri(自動の段数)は使わない(L-803)
    assert set(M.PARAM_KEYS) == set(BASE)
    o = M.V37_ORIGINAL
    assert set(o) == set(BASE)
    assert (o["levels"], o["foot"], o["vola_count"], o["range_count"], o["alert_count"]) == (7, 1, 40, 40, 20)
    assert "auto_levels" not in M.PARAM_KEYS and "fukuri" not in M.PARAM_KEYS
    assert o["range_setting"] == pytest.approx(150 / 600000) and o["over_range_setting"] == pytest.approx(100000 / 600000)
    assert o["vola_setting"] is None and o["beard_ignore"] == 1 and o["b_signal"] is True
    assert (o["entry_setting"], o["exit_setting"], o["break_delay"], o["break_dist"], o["break_len_mult"],
            o["step_setting"], o["step_exit"]) == (2, 0.8, 1, 0.5, 2, 1, 0.8)
    M.check_params(dict(o))
    M.check_params(dict(BASE))


BAD = [
    ("鍵が足りない", lambda p: p.pop("foot")),
    ("知らない鍵", lambda p: p.update(sizemin=0.01)),
    ("段数 0", lambda p: p.update(levels=0)),
    ("段数が整数でない", lambda p: p.update(levels=2.0)),
    ("foot 0", lambda p: p.update(foot=0)),
    ("vola_count 1(割る数 0)", lambda p: p.update(vola_count=1)),
    ("range_count 0", lambda p: p.update(range_count=0)),
    ("alert_count 0", lambda p: p.update(alert_count=0)),
    ("entry_setting ≦ exit_setting", lambda p: p.update(entry_setting=1.0, exit_setting=1.0)),
    ("exit_setting が負", lambda p: p.update(exit_setting=-0.1)),
    ("break_delay が負", lambda p: p.update(break_delay=-1)),
    ("break_len_mult 1", lambda p: p.update(break_len_mult=1)),
    ("break_dist 0", lambda p: p.update(break_dist=0)),
    ("step_setting 0", lambda p: p.update(step_setting=0)),
    ("step_exit 0(L-782 で外した)", lambda p: p.update(step_exit=0)),
    ("比の門が負", lambda p: p.update(range_setting=-0.0001)),
    ("beard_ignore 0", lambda p: p.update(beard_ignore=0)),
    ("真偽の引数に数", lambda p: p.update(b_signal=1)),
    ("NaN", lambda p: p.update(entry_setting=float("nan"))),
]


@pytest.mark.parametrize("name,edit", BAD, ids=[b[0] for b in BAD])
def test_u1_bad_params_refused(name, edit):
    p = dict(BASE)
    edit(p)
    with pytest.raises((ValueError, TypeError, RoadStrategyError)):
        M.check_params(p)


# ================================================================ U2 判定の表(純な関数。v37:991-1037 の写し、SFD・休む時間の枝は無い)
# entry_flag(break_flg, b_signal, flat, last, center, vola, width, entry_setting, range_setting, over_range_setting,
#            vola_setting) / 比の門は「値 × last」と比べる(L-779「その時の価格に合わせた」)
ENTRY_ROWS = [
    # (名前, 引数の差分, 期待)
    ("下に離れた → 買い", dict(last=6999799), 1),
    ("上に離れた → 売り", dict(last=7000201), -1),
    ("ちょうど線の上(買いの線)→ 0(v37:995 は厳しい <)", dict(last=6999800), 0),
    ("ちょうど線の上(売りの線)→ 0", dict(last=7000200), 0),
    ("幅の門が閉じる(幅 < 比 × last)", dict(last=6999799, range_setting=2e-5), 0),
    ("幅の門が開く", dict(last=6999799, range_setting=1e-5), 1),
    ("上の門が閉じる(幅 > 比 × last)", dict(last=6999799, over_range_setting=1e-5), 0),
    ("ボラの門が閉じる(ボラ ≦ 比 × last)", dict(last=6999799, vola_setting=2e-5), 0),
    ("ボラの門が開く", dict(last=6999799, vola_setting=1e-5), 1),
    # ボラ = 比 × last ちょうど(2^-16 × 6,553,600 = 100 は浮動小数でちょうど)→ 「以下」で閉じる(作業者の Q3 で足した)
    ("ボラの門ちょうど(ボラ = 比 × last)→ 閉じる", dict(last=6553600, vola_setting=2.0 ** -16), 0),
    ("ブレイク上・順行 → 買い", dict(break_flg=1, b_signal=1, last=7000000), 1),
    ("ブレイク上・逆行 2 回 → 0", dict(break_flg=1, b_signal=-1, last=7000000), 0),
    ("ブレイク上・b_signal 0・玉なし → 0(静観)", dict(break_flg=1, b_signal=0, last=7000000), 0),
    ("ブレイク上・b_signal 0・玉あり → 買い", dict(break_flg=1, b_signal=0, flat=False, last=7000000), 1),
    ("ブレイク下・順行 → 売り", dict(break_flg=-1, b_signal=-1, last=7000000), -1),
    ("ブレイク下・逆行 → 0", dict(break_flg=-1, b_signal=1, last=7000000), 0),
]
ENTRY_BASE = dict(break_flg=0, b_signal=0, flat=True, last=7000000, center=7000000, vola=100.0, width=100.0,
                  entry_setting=2.0, range_setting=None, over_range_setting=None, vola_setting=None)


@pytest.mark.parametrize("name,diff,want", ENTRY_ROWS, ids=[r[0] for r in ENTRY_ROWS])
def test_u2_entry_flag_table(name, diff, want):
    assert M.entry_flag(**dict(ENTRY_BASE, **diff)) == want


# exit_flag(break_flg, b_signal, entry_flg, side, minutes_held, alert_count, avg, center, held_levels, order_count)
EXIT_ROWS = [
    ("買い玉・普通 → 1", dict(), 1),
    ("買い玉・反対の合図 → 3", dict(entry_flg=-1), 3),
    ("買い玉・2 倍の時間を越えた → 3", dict(minutes_held=41), 3),
    ("買い玉・ちょうど 2 倍 → 2(v37:1010 は厳しい >)", dict(minutes_held=40), 2),
    ("買い玉・時間を越えた → 2", dict(minutes_held=21), 2),
    ("買い玉・ちょうどの時間 → 1", dict(minutes_held=20), 1),
    ("買い玉・建値が中心より悪い → 2", dict(avg=7000001), 2),
    ("買い玉・建値 = 中心 → 1", dict(avg=7000000), 1),
    ("売り玉・普通 → 1", dict(side=-1, avg=7000100), 1),
    ("売り玉・反対の合図 → 3", dict(side=-1, avg=7000100, entry_flg=1), 3),
    ("売り玉・建値が中心より悪い → 2", dict(side=-1, avg=6999999), 2),
    ("ブレイク・反対の合図 → 3", dict(break_flg=1, b_signal=1, entry_flg=-1), 3),
    ("ブレイク・b_signal 0 → 1", dict(break_flg=1, b_signal=0, entry_flg=1), 1),
    ("ブレイク・逆行 2 回 → 2", dict(break_flg=1, b_signal=-1, entry_flg=0), 2),
    ("ブレイク・順行・段が上限 → 1", dict(break_flg=1, b_signal=1, entry_flg=1, held_levels=7), 1),
    ("ブレイク・順行・段が上限未満 → 0", dict(break_flg=1, b_signal=1, entry_flg=1, held_levels=6), 0),
    ("ブレイク中は時間で決済しない", dict(break_flg=1, b_signal=1, entry_flg=1, held_levels=6, minutes_held=1000), 0),
]
EXIT_BASE = dict(break_flg=0, b_signal=0, entry_flg=0, side=1, minutes_held=0, alert_count=20, avg=6999900,
                 center=7000000, held_levels=2, order_count=7)


@pytest.mark.parametrize("name,diff,want", EXIT_ROWS, ids=[r[0] for r in EXIT_ROWS])
def test_u2_exit_flag_table(name, diff, want):
    assert M.exit_flag(**dict(EXIT_BASE, **diff)) == want


# exit_price(exit_flg, break_flg, side, center, vola, avg, held_levels, exit_setting, step_exit)
PRICE_ROWS = [
    ("レンジ・買い玉・1 → 中心 − exit × ボラ(L-782)", dict(), 7000000 - 80.0),
    ("レンジ・売り玉・1 → 中心 + exit × ボラ", dict(side=-1), 7000000 + 80.0),
    ("買い玉・2 → 中心 と 建値 + ボラ × step_exit ÷ 段数 の低い方(v37:912)・建値の側", dict(exit_flg=2), 6999950.0),
    ("買い玉・2・中心の側", dict(exit_flg=2, avg=6999990), 7000000),
    ("売り玉・2 → 高い方(v37:898)", dict(exit_flg=2, side=-1, avg=7000300), 7000250.0),
    ("売り玉・2・中心", dict(exit_flg=2, side=-1, avg=7000020), 7000000),
    ("ブレイク・買い玉・1 → 建値 + ボラ × step_exit ÷ 段数(L-789)", dict(break_flg=1, avg=7000000), 7000050.0),
    ("ブレイク・売り玉・1 → 建値 − …", dict(break_flg=-1, side=-1, avg=7000000), 6999950.0),
]
PRICE_BASE = dict(exit_flg=1, break_flg=0, side=1, center=7000000, vola=100.0, avg=6999900, held_levels=2,
                  exit_setting=0.8, step_exit=1.0)


@pytest.mark.parametrize("name,diff,want", PRICE_ROWS, ids=[r[0] for r in PRICE_ROWS])
def test_u2_exit_price_table(name, diff, want):
    assert M.exit_price(**dict(PRICE_BASE, **diff)) == pytest.approx(want)
