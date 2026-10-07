"""The ledger of strategies for the バックテスト tab (戦略の台帳): theme -> strategy -> what it is, with the source of every line.

A road run (road/ beside record.json) names its strategy in record.json: config.strategy.module (kind = "module") or
setup.name. This file says, for such a name, which theme it belongs to, what the strategy is, and what its params mean.
Every `text` below was written from the file named in its `source` and says nothing that source does not say. A strategy
that is not here is still listed (under THEME_UNLISTED) with the sentence 「説明が台帳に無い」: nothing is hidden because
the ledger lacks a line (the tab never decides what to show from this ledger; it only adds words).

    STRATEGIES   module name -> {theme, title, fake, description: [{text, source}], params: {key: {label, source}}}
    THEMES       theme id -> {title, summary, source}

Which params a family varies is NOT written here: road_catalog reads them from the runs' record.json (config) and only
looks the labels up here.
"""
from __future__ import annotations

from typing import Optional

THEME_UNLISTED = "unlisted"
THEME_FAKE = "fake"
NOT_IN_LEDGER = "説明が台帳に無い"

_FRAMING = "docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/FRAMING_V37.md"
_LEGACY = "docs/legacy/matilda_for_TaroCamp37.py"
_RECORD = "docs/DISCUSSIONS/2026-10-06_held_batches/RECORD_FORM_L766.md"

THEMES: dict[str, dict] = {
    "matilda": {
        "title": "マチルダ(段数のある指値の戦略)",
        "summary": "直近の足の高値・安値の中心から離れた値段に指値の段を積み、中心の側へ戻ったところで利確する戦略を、"
                   "道(1 本の記録の形)で測った走らせ。",
        "source": f"{_FRAMING} §1・§4",
    },
    THEME_FAKE: {
        "title": "作り物(表示の確かめ用)",
        "summary": "ダッシュボードの表示を確かめるために作った走らせ。戦略は本物ではなく、結果は相場の結論に使わない。"
                   "足は本物の bitFlyer FX_BTC_JPY の 1 分足(封印の前)。",
        "source": "tests/road_fake_runs/README.txt",
    },
    THEME_UNLISTED: {
        "title": "台帳に無い戦略",
        "summary": "戦略の台帳に載っていない戦略の走らせ。説明は台帳に無い。",
        "source": "src/bot/monitoring/road_strategies.py",
    },
}

STRATEGIES: dict[str, dict] = {
    "bot.strategy.matilda_v37": {
        "theme": "matilda",
        "title": "マチルダ(v37)",
        "fake": False,
        "description": [
            {"text": "前提(測る前に置いた読み): bitFlyer FX_BTC_JPY は 1 分足の細かさで、直近 40 本の高値・安値の中心から "
                     "ボラ × entry_setting 離れた値段に来た後、中心の側の ボラ × exit_setting の線まで戻ることが、"
                     "逆へ伸びて時間切れ・ブレイクになることより多いので、マチルダは稼ぐ。",
             "source": f"{_FRAMING} §1 前提"},
            {"text": "建て: 合図の足で、1 段目(中心 ∓ entry_setting × ボラ)から段数の上限までを指値で一度に置く。"
                     "次の足から当てる(範囲の内なら指値の値段、有利な側の外なら始値)。",
             "source": f"{_FRAMING} §4"},
            {"text": "利確: 中心 ± exit_setting × ボラの線への指値。良い側は建てと同じ足から、悪い側は次の足から当てる。"
                     "成行(時間切れの 2 倍・反対の建ての合図)は次の足の始値。",
             "source": f"{_FRAMING} §4"},
            {"text": "量: 20 万円 × 70% ÷ 段数 ÷ 建てた時の値段(0.001 BTC 未満切り捨て)。取引の中の段の量は、建玉を持った時点(最初の段)の量にそろえる"
                     "(L-781)。量が 0 になる段は「量が 0 で出さない」として注文の表に残る。",
             "source": f"{_FRAMING} §0(L-745・L-746・L-781)、{_RECORD} §6"},
            {"text": "ブレイク中の建てと利確(オーナーが L-789「あってる」で確定): 建ては合図の足の終値から step ずつ、利確は建値 ± ボラ × step_exit ÷ 段数。",
             "source": f"{_FRAMING} §8(L-789)"},
            {"text": "約定の範囲は悲観側・楽観側の 2 つを走らせて両方記録する。経費(手数料・建玉の管理料・SFD)は帳簿の損益に入れない(経費の前で数える)。",
             "source": f"{_FRAMING} §3、{_FRAMING} §4(L-769)"},
            {"text": "原典: 太郎キャンプ版 v37 のマチルダ(bitFlyer の自動売買)。",
             "source": _LEGACY},
        ],
        "params": {
            "entry_setting": {"label": "建ての離れ(ボラの倍数)", "source": f"{_FRAMING} §5"},
            "exit_setting": {"label": "利確の線(ボラの倍数)", "source": f"{_FRAMING} §5"},
            "vola_count": {"label": "ボラを見る本数", "source": f"{_FRAMING} §5"},
            "range_count": {"label": "レンジを見る本数", "source": f"{_FRAMING} §5"},
            "alert_count": {"label": "静観を見る長さ", "source": f"{_FRAMING} §5・§8"},
            "step_setting": {"label": "段の間隔(ボラの倍数)", "source": f"{_FRAMING} §5"},
            "step_exit": {"label": "段ごとの利確(ボラの倍数)", "source": f"{_FRAMING} §5"},
            "break_delay": {"label": "ブレイクを見る遅れ", "source": f"{_FRAMING} §5"},
            "breakexitsize": {"label": "ブレイクの決済の段数", "source": f"{_FRAMING} §5"},
            "foot": {"label": "戦略が見る足(分)", "source": f"{_FRAMING} §5"},
        },
    },
    "bot.strategy.fake_road_demo": {
        "theme": THEME_FAKE,
        "title": "作り物の段のある指値(マチルダではない)",
        "fake": True,
        "description": [
            {"text": "本物の戦略ではない。表示の確かめ用に作った小さな道の戦略。窓の高値・安値の中心と実体の平均(ボラ)から、"
                     "終値が 中心 ∓ k × ボラ の外に出たら合図(向き long / short)の発生、内側に戻ったら消失。",
             "source": "tests/road_fake_runs/fake_road_demo.py の docstring"},
            {"text": "合図の間、中心 ∓ k × ボラ に指値を置き、段は 1 × ボラずつ有利な側に levels まで積む。約定しない指値は 3 本たったら"
                     "取り消す。建玉があれば足ごとに決済の指値を取り消して置き直し、40 本たったら出ている注文を取り消して close の成行。"
                     "zero_every > 0 なら、その回数目の段だけ段数 200 で出して量を 0 にする(量が 0 で出さない段の見本)。",
             "source": "tests/road_fake_runs/fake_road_demo.py の docstring"},
        ],
        "params": {
            "levels": {"label": "段数", "source": "tests/road_fake_runs/fake_road_demo.py"},
            "window": {"label": "窓の本数", "source": "tests/road_fake_runs/fake_road_demo.py"},
            "k": {"label": "線の離れ(ボラの倍数)", "source": "tests/road_fake_runs/fake_road_demo.py"},
            "zero_every": {"label": "量 0 の段を入れる間隔", "source": "tests/road_fake_runs/fake_road_demo.py"},
        },
    },
    "bot.strategy.road_scene_test": {
        "theme": THEME_FAKE,
        "title": "作り物の場面(受け入れ試験の戦略)",
        "fake": True,
        "description": [
            {"text": "道の記録の受け入れ試験(tests/road/road_scene_strategy.py)の小さな場面の戦略。params の mode で場面を選ぶ"
                     "(例 limit_cancel = 終値の半分の届かない指値を出して後で取り消す)。本物の戦略ではない。",
             "source": "tests/road/road_scene_strategy.py の docstring(メインの作業ブランチ)"},
        ],
        "params": {
            "mode": {"label": "場面", "source": "tests/road/road_scene_strategy.py"},
            "levels": {"label": "段数", "source": "tests/road/road_scene_strategy.py"},
            "open_bar": {"label": "合図を出す足の番号", "source": "tests/road/road_scene_strategy.py"},
            "close_bar": {"label": "決済・取り消しをする足の番号", "source": "tests/road/road_scene_strategy.py"},
        },
    },
}


def strategy_entry(name: Optional[str]) -> dict:
    """The ledger entry of a strategy name, or a stand-in that says 「説明が台帳に無い」 (never None)."""
    hit = STRATEGIES.get(name or "")
    if hit is not None:
        return hit
    return {"theme": THEME_UNLISTED, "title": name or "(戦略の名前が記録に無い)", "fake": False,
            "description": [{"text": f"{NOT_IN_LEDGER}。戦略の名前(record.json): {name or '(無し)'}。"
                                     "台帳 src/bot/monitoring/road_strategies.py に、出所つきで書くまでこのまま出す。",
                             "source": "record.json の config.strategy.module / setup.name"}],
            "params": {}}


def param_label(name: Optional[str], key: str) -> tuple[str, str]:
    """(label, source) of a config key (path under config.strategy.params stripped of its prefix), else (key, record.json's path)."""
    p = (STRATEGIES.get(name or "") or {}).get("params", {}).get(key)
    if p:
        return p["label"], p["source"]
    return key, "record.json の config(ledger に説明が無い)"
