"""The dashboard's バックテスト tab: the ledger of themes (テーマ台帳).

    THEMES   theme (category) -> strategy -> the run groups ("組") that hold its runs
    AXES     the config keys that differ from run to run inside one strategy (族の軸) and their Japanese labels

A "組" is the sub-path `backtest_view.find_runs` reports for a run directly under backtest_runs_shared/
(k1_newenv_a, k1_env_fixes/pipeline, ...). The ledger maps 組 -> strategy -> theme; a later theme (for example the
research cards of docs/RESEARCH/cards) is one more entry of THEMES -- nothing else in the tab names a theme.
A run whose 組 is in no strategy of the ledger is still listed, under 「台帳に無い実行」 (catalog() in
backtest_chart.py), so a run is never hidden by a missing ledger line.

Every title / description / label below was written from the sources it names (`sources`), and says nothing the
source does not say. Where a statement comes from a run's own record.json (config / purpose / components), the
source is "record.json の <field>". The axes and their values are NOT written here: backtest_chart.catalog() reads
them from each run's record.json; this file only says which axes a strategy has, and what a key and a value mean.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Callable, Optional

K1_PREREG = "docs/PHASE2/K1/PREREG.md"
K1_XPREREG = "docs/PHASE2/K1/XVENUE_PREREG.md"
K1_WICK = "src/bot/strategy/k1_wick.py"
ENV_DELEG = "docs/DATA/delegations/20260927_k1_env_fixes.md"
CLOSE_DELEG = "docs/DATA/delegations/20261001_k1_stage_g_close.md"
K1_XVENUE = "src/bot/strategy/k1_xvenue.py"

UNLISTED_THEME = "unlisted"
UNLISTED_TITLE = "台帳に無い実行"


# ---- the axes -------------------------------------------------------------------------------------------------
def _cfg(rec: dict) -> dict:
    return rec.get("config") or {}


def _params(rec: dict) -> dict:
    """The K1 parameters of a run through bot.bt.pipeline (config.strategy.params = {s, b, strength})."""
    st = _cfg(rec).get("strategy")
    return (st.get("params") or {}) if isinstance(st, dict) else {}


def _foot(rec: dict) -> Any:
    return _cfg(rec).get("foot_min")


def _gate(rec: dict) -> Optional[str]:
    g = _cfg(rec).get("gate")
    if isinstance(g, dict) and "s" in g and "b" in g:
        return f"s{g['s']}/b{g['b']}"
    p = _params(rec)
    if "s" in p and "b" in p:
        return f"s{p['s']}/b{p['b']}"
    return None


def _strength(rec: dict) -> Any:
    v = _cfg(rec).get("strength")
    return v if v is not None else _params(rec).get("strength")


def _day(ns: Any) -> Optional[str]:
    if type(ns) is not int:
        return None
    return dt.datetime.fromtimestamp(ns // 10**9, tz=dt.timezone.utc).strftime("%Y-%m-%d")


def _engine_ns(rec: dict) -> tuple[Optional[int], Optional[int]]:
    """(first_time_ns, last_time_ns) of the run: engine.* or, for a run through bot.bt.pipeline, its first instrument."""
    eng = rec.get("engine") or {}
    if "first_time_ns" not in eng:
        for rng in eng.values():
            if isinstance(rng, dict):
                for per in rng.values():
                    if isinstance(per, dict) and "first_time_ns" in per:
                        return per.get("first_time_ns"), per.get("last_time_ns")
    return eng.get("first_time_ns"), eng.get("last_time_ns")


def _period(rec: dict) -> Optional[str]:
    a, b = _engine_ns(rec)
    if a is None or b is None:
        return None
    return f"{_day(a)}〜{_day(b - 1)}"


def _version(rec: dict) -> Optional[str]:
    g = rec.get("git_sha")
    return f"{str(g)[:7]} / 差分 {str(rec.get('diff_hash'))[:6]}" if g else None


def _prepare(rec: dict) -> Optional[str]:
    return _cfg(rec).get("prepare") or "(記載なし)"


def _plain(key: str) -> Callable[[dict], Any]:
    return lambda rec: _cfg(rec).get(key)


#: key -> {label, source, get(record) -> value or None, values: {raw value: (label, note)}, order(value) -> sort key}
AXES: dict[str, dict] = {
    "foot_min": {
        "label": "足の長さ", "get": _foot, "unit": "分",
        "source": f"{K1_PREREG} §3.1 族の表「足 foot」(1 / 3 / 5 / 15 / 30 / 60 分。秒バーを UTC の壁時計で foot 分に畳む = §1)",
        "values": {}, "order": lambda v: float(v),
    },
    "gate": {
        "label": "門(小門 s / 大門 b)", "get": _gate,
        "source": f"{K1_PREREG} §3.0・§3.1(門は bp 建て = §3.2)と {K1_WICK} の docstring「s: off = 小門の枝を使わない, - = 長さの下限なし, "
                  "10/19/30 = bp。b: - = 大門の枝を使わない, 24/40 = bp」",
        "values": {
            "s-/b-": ("s-/b-", "v03 のまま(門なし。実体条件だけ)"),
            "s19/b24": ("s19/b24", "オーナーが当時使っていた規則(bp 建てに置き換えた版)"),
            "s19/b-": ("s19/b-", "大門の枝を外した版(b の寄与を分離する)"),
        },
        "note_source": f"{K1_PREREG} §3.1「必ず入れる 3 つの参照点」",
        "order": lambda v: _gate_order(v),
    },
    "strength": {
        "label": "強さ", "get": _strength,
        "source": f"{K1_PREREG} §3.1 族の表「強さ」: 強い(下ヒゲ陽線・上ヒゲ陰線)/ 弱い(上ヒゲ陽線・下ヒゲ陰線)/ 両方",
        "values": {"strong": ("強い", "下ヒゲ陽線・上ヒゲ陰線"), "weak": ("弱い", "上ヒゲ陽線・下ヒゲ陰線"),
                   "both": ("両方", "強い・弱いの両方で建てる")},
        "order": lambda v: ("strong", "weak", "both").index(v) if v in ("strong", "weak", "both") else 9,
    },
    "mode": {
        "label": "値付けと行動の形", "get": _plain("mode"),
        "source": f"{K1_XVENUE} の docstring「モード」と {K1_XPREREG} §1 参考列",
        "values": {
            "design": ("設計どおり", "シグナルは海外の足、約定は bitFlyer の次の足の終値(H3)。XVENUE_PREREG §1 の「執行」"),
            "sameclose": ("同じ足の終値(参考)", "H3 を外し、同じ窓の bitFlyer の終値で約定する。取れない価格(XVENUE_PREREG §1 参考列 iii)"),
            "single": ("海外の終値(参考)", "1 本の流れ(海外の足だけ)。海外の足の終値で値付けする(XVENUE_PREREG §1 参考列 i)"),
        },
        "order": lambda v: ("design", "sameclose", "single").index(v) if v in ("design", "sameclose", "single") else 9,
    },
    "instrument": {
        "label": "値付けの銘柄", "get": _plain("instrument"),
        "source": f"record.json の config.instrument と {K1_XVENUE} の PRODUCTS(FX_BTC_JPY = bitFlyer・円建て、BTCUSDT = Binance・USDT)",
        "values": {"FX_BTC_JPY": ("bitFlyer FX_BTC_JPY", "円建て"), "BTCUSDT": ("Binance BTCUSDT", "USDT 建て"),
                   "XBTUSD": ("BitMEX XBTUSD", "")},
        "order": lambda v: str(v),
    },
    "period": {
        "label": "期間", "get": _period,
        "source": "record.json の engine.first_time_ns 〜 last_time_ns(UTC の日付。終わりの日を含む)",
        "values": {}, "order": lambda v: str(v),
    },
    "prepare": {
        "label": "入力の作り方", "get": _prepare,
        "source": f"record.json の config.prepare と {K1_XVENUE} の docstring「入力の 2 つの形」",
        "values": {"join_fold": ("生の 1 分足を結合・畳み", "海外と bitFlyer の 1 分足を分で内部結合し、foot 分に畳んで使う"),
                   "(記載なし)": ("記載なし", "この record の config に prepare の記載が無い")},
        "order": lambda v: str(v),
    },
    "version": {
        "label": "実行のコード版", "get": _version,
        "source": "record.json の git_sha と diff_hash(同じ設定の実行が複数あるときだけ出す)",
        "values": {}, "order": lambda v: str(v),
    },
}


def _gate_order(v: str) -> tuple:
    from bot.strategy.k1_wick import BIG, SMALL  # noqa: PLC0415 -- the strategy module's own order of the gate labels
    try:
        s, b = v[1:].split("/b")
        return (SMALL.index(s), BIG.index(b))
    except (ValueError, IndexError):
        return (99, 99)


# ---- the ledger -----------------------------------------------------------------------------------------------
K1_SOURCES = [f"{K1_PREREG} §0・§3.0・§3.1・§4.2", f"{K1_WICK} の docstring と K1WickStrategy.on_event"]
K1X_SOURCES = [f"{K1_XPREREG} §0・§1", f"{K1_XVENUE} の docstring"]
ENV_SOURCES = ["record.json の purpose・config・components・git_sha(各実行の記録)",
               "record.json の config.costs.source「委任文 20260927_k1_env_fixes §2-2: 費用 0・遅延 0」"]

THEMES: list[dict] = [
    {
        "id": "k1_wick",
        "title": "ヒゲの後は戻るか(K1)",
        "summary": "確定した足の形(ヒゲの向き・長さ)だけから、後続のリターンが予測できるかを調べた研究。",
        "sources": [f"{K1_PREREG} §0「この単位が答える問い」"],
        "strategies": [
            {
                "id": "k1_wick_xbtusd",
                "kind": "strategy",
                "title": "ヒゲ反発(BitMEX XBTUSD・探索区間 2017〜2019)",
                "groups": ["k1_newenv_a"],
                "description": [
                    "足(1〜60 分)ごとに、上ヒゲと下ヒゲのうち長い方(勝った側。int() で切り捨てて比較)の向きと長さを見る。",
                    "上ヒゲが長ければ売り、下ヒゲが長ければ買いのシグナルとする。長さは bp 建ての門で絞る"
                    "(小門 s: ヒゲが s bp 以上かつ実体より長い / 大門 b: ヒゲが b bp 以上なら実体を問わない。どちらかを満たせば出る)。",
                    "建てるのはシグナルが出た足の終値で、成行・1 単位。同じ向きのシグナルでは増し玉をしない。",
                    "決済は次のどちらか早い方。(1)無効化: 選んだ強さで建てられない足(選んだ強さに合わないシグナルの足も含む)で、足の色が建玉と反対かつ、"
                    "買いは終値が下の先端以下、売りは終値が上の先端以上になったとき。(2)選んだ強さのシグナルが反対向きに出たとき。",
                    "反対向きのシグナルが「強い」(下ヒゲ陽線・上ヒゲ陰線)ならドテン(決済して反対に建て直す)、「弱い」なら決済だけ。経費は引かない。",
                    "この実行の期間は探索区間 2017-01-01〜2019-12-31。判定区間は 2020-01-01〜2021-12-31 で、2026-09-10 に一度だけ開けた。",
                ],
                "sources": [f"{K1_PREREG} §2(分割)・§3.0(シグナルの条件)・§3.1(族)・§4.2(決済)",
                            f"{K1_WICK} の docstring(RESULT.md 1.4: 成行を足の終値で・経費なし)と K1WickStrategy.on_event 140-163 行(無効化・反対シグナル・ドテン・決済のみ)",
                            "docs/PHASE2/K1/RESULT.md 3 行目(判定区間 2020-2021 は 2026-09-10 に一度だけ開けた)"],
                "axes": ["foot_min", "gate", "strength", "instrument", "version"],
            },
            {
                "id": "k1_xvenue",
                "kind": "strategy",
                "title": "取引所横断(海外のヒゲを bitFlyer の価格で値付け)",
                "groups": ["k1_newenv_g"],
                "description": [
                    "問いは「海外のヒゲのシグナルは bitFlyer の値動きに移るか」。シグナルは海外取引所(Binance BTCUSDT 現物)の足で作り、注文の価格だけ bitFlyer を使う。",
                    "ヒゲの門(RESULT.md 1.3 と同じ)を通った足で、実体が勝った側のヒゲ以上なら実体を逆張りにする(H1)。取るのは「弱い」シグナルだけ。",
                    "海外の足 i のシグナルで、bitFlyer の足 i+1 の終値で建て・閉じる(H3)。1 単位。",
                    "決済はヒゲ先端の無効化を使わず、海外の足で判定した反対向きのシグナルだけ(H2a)。弱いシグナルは決済のみで、建て直さない。",
                    "「値付けと行動の形」を変えると、同じ窓の終値で約定する参考列(取れない価格)と、海外の終値で値付けする参考列も見られる。経費は引かない。",
                ],
                "sources": [f"{K1_XPREREG} §0(問い)・§1(設計・参考列)", f"{K1_XVENUE} の docstring(H1・H2a・H3・モード・費用 0)"],
                "axes": ["mode", "instrument", "foot_min", "gate", "strength", "period", "prepare", "version"],
            },
        ],
    },
    {
        "id": "env_check",
        "title": "バックテスト環境の確かめ",
        "summary": "戦略の良し悪しを比べるためではなく、バックテスト環境(統合実行 bot.bt.pipeline)の修正を確かめるための実行。",
        "sources": [f"{ENV_DELEG} §1「そこで出る欠陥を直す」(D-1〜D-4 の直しの確かめ)",
                    f"{CLOSE_DELEG} §2 G-3(封印の台帳に載ったファイルを範囲つきで入力にする)", *ENV_SOURCES],
        "strategies": [
            {
                "id": "env_pipeline",
                "kind": "env_check",
                "title": "環境の確かめ①(pipeline)",
                "groups": ["k1_env_fixes/pipeline"],
                "description": [
                    "これは戦略の成績を見る実行ではなく、バックテスト環境の修正の確かめの実行(目的欄は「研究」、組の名前は k1_env_fixes)。",
                    "中身は K1 のヒゲ戦略(bot.strategy.k1_wick の pipeline_strategy)を、統合実行 bot.bt.pipeline で BitMEX XBTUSD の 60 分足・2017〜2019 に走らせたもの。",
                    "設定は小門 s・大門 b・強さ(params)の組ごとに 1 本。費用 0・遅延 0、口座の通貨は USD。",
                    "約定の幅は optimistic と pessimistic の 2 つ(どちらも tier 2)で、取引の一覧には両方が入っている。",
                ],
                "sources": ENV_SOURCES,
                "axes": ["gate", "strength", "version"],
            },
            {
                "id": "env_pipeline_r2",
                "kind": "env_check",
                "title": "環境の確かめ②(pipeline_r2)",
                "groups": ["k1_env_fixes/pipeline_r2"],
                "description": [
                    "これは戦略の成績を見る実行ではなく、バックテスト環境の修正の確かめの実行(目的欄は「研究」、組の名前は k1_env_fixes)。",
                    "「環境の確かめ①」と同じ設定の組(小門 s・大門 b・強さ)を、別のコード版(record の git_sha と戦略モジュールの sha256 が異なる)で走らせた実行。",
                    "中身・データ・費用 0・遅延 0・口座の通貨 USD・約定の幅(optimistic / pessimistic)は①と同じ記録になっている。",
                ],
                "sources": ENV_SOURCES,
                "axes": ["gate", "strength", "version"],
            },
            {
                "id": "env_stage_g_close",
                "kind": "env_check",
                "title": "環境の確かめ③(範囲つきの入力・G-3)",
                "groups": ["k1_newenv_g_close"],
                "description": [
                    "これは戦略の成績を見る実行ではなく、環境の欠陥 G-3 の確かめの実行(委任文 20261001_k1_stage_g_close §2)。G-3 は、封印の台帳に載ったファイルを、境より前の範囲で入力にできること。",
                    "中身は取引所横断(海外のヒゲを bitFlyer の価格で値付け)を、生の 1 分足(Binance BTCUSDT と bitFlyer FX_BTC_JPY の 2018〜2021)から結合・畳みして走らせたもの。",
                    "設定は record の config から読める範囲で、モードは設計どおり・門 s19/b24・強さ弱い、足は 5 分と 15 分。費用 0。",
                ],
                "sources": [f"{CLOSE_DELEG} §2 G-3", "record.json の config(prepare = join_fold・streams・mode・gate・strength)と data(2018〜2021 の 1 分足)",
                            f"{K1_XVENUE} の docstring「入力の 2 つの形」"],
                "axes": ["foot_min", "version"],
            },
        ],
    },
]


def strategy_groups() -> dict[str, tuple[dict, dict]]:
    """組 -> (theme, strategy) for every group of the ledger."""
    out: dict[str, tuple[dict, dict]] = {}
    for th in THEMES:
        for st in th["strategies"]:
            for g in st["groups"]:
                if g in out:
                    raise ValueError(f"group {g!r} is in two strategies of the ledger")
                out[g] = (th, st)
    return out


# =================================================================================================================
# The research cards (docs/RESEARCH/cards/<card>/CARD.md): one theme per card. The variants are NOT listed here: they are
# collected from backtest_runs_shared/cards/manifest.json (backtest_cards.py); this ledger says what the card is (title,
# description, sources), which price store its trades are on, how a variant's NAME splits into axes, and what each axis
# value means. A variant whose name no family pattern splits is listed under 「分解の規則が台帳に無い変種」 (never hidden);
# a token with no label here is shown as it is with a note (the Japanese label is missing).
# =================================================================================================================
CARDS_DIR = "docs/RESEARCH/cards"
W4_SCRIPTS = "scripts/w4_measure"
RUN_V2 = f"{W4_SCRIPTS}/run_v2.py"
RUN_B2 = f"{W4_SCRIPTS}/run_b2.py"
OTHER_FAMILY = "other"
OTHER_TITLE = "分解の規則が台帳に無い変種"


def _card(card: str, section: str) -> str:
    return f"{CARDS_DIR}/{card}/CARD.md {section}"


def _num_order(token: str) -> float:
    return float(token)


#: axis key -> {label, source, values: {token: (label, note)} (insertion order = display order), unit (numeric tokens),
#: numeric}. A card axis is named by what the name part means; `source` says where the split and the meanings come from.
CARD_AXES: dict[str, dict] = {
    "variant": {"label": "変種名", "numeric": False, "source": "manifest.json の variants[].variant(名前の分解の規則が台帳に無い変種を、名前のまま並べる)",
                "values": {}},
    "c2_series": {
        "label": "シグナルを作る海外の系列", "numeric": False,
        "source": f"{RUN_V2} の C2_VARIANTS(変種名の先頭の a / b / c = シグナルの系列)と {_card('c2_owner_xvenue_wick', '「変種と測る順」の表')}",
        "values": {
            "a": ("Binance 現物 BTCUSDT", "高レバ取引所ではない代理(CARD.md 意図の地図 I-11a)。期間 2017-08-17T15:00Z〜2023-12-17T15:00Z"),
            "b": ("Binance USD-M 先物 BTCUSDT", "先物の系列。期間 2020-01-01T15:00Z〜2023-12-17T15:00Z"),
            "c": ("BitMEX XBTUSD(1 秒足から作った 1 分足)", "期間 2017-08-17T15:00Z〜2021-12-31T15:00Z"),
        }},
    "c2_foot": {
        "label": "海外の足の長さ", "numeric": True, "unit": "分足",
        "source": f"{RUN_V2} の --foot(変種名の末尾 <N>m = 足の分数)と {_card('c2_owner_xvenue_wick', '「水準とその出所」足の長さ(既定 15 分、変種 1・3・5・15・30・60 分)')}",
        "values": {}},
    "c3_window": {
        "label": "上乗せの分布を見る直近の窓", "numeric": False,
        "source": f"{RUN_V2} の --window(変種名 = 窓)と {_card('c3_yen_premium_revert', '「水準とその出所」窓 1 時間 / 1 日 / 1 週')}",
        "values": {"1h": ("1 時間", ""), "1d": ("1 日", ""), "1w": ("1 週", "")}},
    "c4_part": {
        "label": "部品(切る・変える)", "numeric": False,
        "source": f"{RUN_B2} の C4_KW(変種名 <部品>_<端> の <部品> = C4OwnerMatildaRange へ渡す引数の組)と {_card('c4_owner_matilda_range', '「水準とその出所」部品の切り替え width_gate・trend_gate・time_exit・levels、on_trend')}",
        "values": {
            "full": ("全部入り", "幅の門・静観の門・時間成行・段(最大 7 段)をすべて使う"),
            "no_width": ("幅の門なし", "幅 ÷ 終値が小さすぎる局面でも建てる(width_gate = False)"),
            "no_trend": ("静観の門なし", "窓の幅 ÷ 平均実体が大きい(一方向の動きの)間も静観しない(trend_gate = False)"),
            "no_time": ("時間成行なし", "40 分たっても時間で閉じない(time_exit = False)"),
            "no_levels": ("段なし(1 段)", "段を積まず、持ち高は −1 / 0 / +1(levels = False)"),
            "follow": ("一方向の動きの間は向きに入る(逆転順張り)", "持ち高 0 からも動きの向きに 1 段入る(on_trend = follow)"),
            "core": ("4 部品とも切る", "幅の門・静観の門・時間成行・段をすべて切る(width_gate・trend_gate・time_exit・levels = False)"),
        }},
    "c4_range": {
        "label": "レンジの上端・下端", "numeric": False,
        "source": f"{RUN_B2} の make_card(変種名 <部品>_<端> の <端> = range_from)と {_card('c4_owner_matilda_range', '「水準とその出所」レンジの端 range_from')}",
        "values": {"body": ("実体の端", "足の実体の上端・下端でレンジを作る(既定。原典 v37 はヒゲを捨てる)"),
                   "wick": ("高値・安値(ヒゲ込み)", "足の高値・安値でレンジを作る")}},
    "c4_bar": {
        "label": "足の長さ", "numeric": True, "unit": "分足",
        "source": f"{RUN_B2} の make_card(変種名 m_b<足>_w<窓>_e<離れ>_<利確> の b = bar_min)と {_card('c4_owner_matilda_range', '「地図のための値の表の拡張」足 5 分')}",
        "values": {}},
    "c4_win": {
        "label": "レンジの窓", "numeric": True, "unit": "分",
        "source": f"{RUN_B2} の make_card(変種名の w = window_min)と {_card('c4_owner_matilda_range', '「地図のための値の表の拡張」窓 10・20・80・160 分(既定 40 分)')}",
        "values": {}},
    "c4_entry": {
        "label": "入りの離れ(中心からの距離)", "numeric": True, "unit": "× 平均実体",
        "source": f"{RUN_B2} の make_card(変種名の e = entry_setting)と {_card('c4_owner_matilda_range', '「水準とその出所」入りの離れ entry_setting(既定 2 × 平均実体)')}",
        "values": {}},
    "c4_tp": {
        "label": "利確の形", "numeric": False,
        "source": f"{RUN_B2} の C4_TP(変種名の末尾 = exit_mode と exit_setting の組)と {_card('c4_owner_matilda_range', '「水準とその出所」利確の形 exit_mode(0 ドテン / 1 センター付近 / 2 値幅)')}",
        "values": {
            "v37": ("原典 v37 の利確(既定)", "建値から按分した値幅 0.8 × 平均実体。向きを持って 20 分たつか建値が中心より損の側なら、線を中心まで緩める(exit_mode 2)"),
            "c08": ("中心から 0.8 × 平均実体", "売りは中心 + 0.8 × 平均実体 以下、買いは中心 − 0.8 × 平均実体 以上で 0(exit_mode 1、exit_setting 0.8)"),
            "c0": ("中心ちょうど", "中心に届いたら 0(exit_mode 1、exit_setting 0.0)"),
            "dote": ("利確の線なし(ドテン)", "反対の入りの条件で反対へ回る(exit_mode 0)"),
        }},
    "c4_fill": {
        "label": "足の中の値動きの順が決まらないとき", "numeric": False,
        "source": f"{W4_SCRIPTS}/c4_limit_run.py の --fill-side(変種名 limit_v37_<good|bad>)と src/bot/research/matilda_limit_sim.py の docstring「決まらない足」",
        "values": {"good": ("損益の良い方の道で進める(良い側)", "1 分足は高値と安値のどちらが先かを持たないので、2 通りの道のうち損益の良い方を採る"),
                   "bad": ("損益の悪い方の道で進める(悪い側)", "2 通りの道のうち損益の悪い方を採る")}},
    "c6_gap": {
        "label": "ギャップの定義", "numeric": False,
        "source": f"{RUN_B2} の CARDS(c6 の変種 usdjpy / btc)と {_card('c6_weekend_gap_revert', '原文の次の節「「週末」「ギャップ」が何を指すか」')}",
        "values": {"usdjpy": ("USDJPY の週明けの窓", "USDJPY の週明けの最初の値と前の週の最後の値の差をギャップとする(持つのは FX_BTC_JPY)"),
                   "btc": ("為替が閉まっていた間の BTC の値動き", "為替の市場が閉まっていた間の FX_BTC_JPY の値動きをギャップとする")}},
    "c7_window": {
        "label": "幅を決める窓", "numeric": False,
        "source": f"{RUN_B2} の CARDS(c7 の変種 1h / 1d / 1w)と {_card('c7_barrier_race', '「水準とその出所」幅の窓 1 時間・1 日・1 週')}",
        "values": {"1h": ("1 時間", ""), "1d": ("1 日", ""), "1w": ("1 週", "")}},
    "c8_session": {
        "label": "セッションの区切り", "numeric": False,
        "source": f"{RUN_B2} の CARDS(c8 の変種 jst_day / bf_maint)と {_card('c8_session_mean_revert', '「水準とその出所」セッションの区切り')}",
        "values": {"jst_day": ("日本時間の日", "日本時間の 0 時(UTC の 15 時)から翌 0 時まで"),
                   "bf_maint": ("bitFlyer の保守の始まりから翌日", "19:00 UTC(日本時間の 4 時)から翌 19:00 UTC まで")}},
}


def card_axis_label(key: str, token: str) -> tuple[str, str]:
    """(label, note) of one axis value; a token with no entry here is shown as it is, and the note says so."""
    spec = CARD_AXES.get(key)
    if spec is None:
        return str(token), "台帳にこの軸の説明が無い"
    known = spec["values"].get(token)
    if known:
        return known[0], known[1]
    if spec.get("numeric"):
        return f"{token} {spec['unit']}", ""
    return str(token), "台帳にこの値の日本語の説明が無い"


def card_axis_order(key: str, token: str) -> tuple:
    spec = CARD_AXES.get(key) or {}
    if spec.get("numeric"):
        try:
            return (0, _num_order(token), "")
        except ValueError:
            return (2, 0.0, str(token))
    vals = list(spec.get("values", {}))
    return (0, float(vals.index(token)), "") if token in vals else (1, 0.0, str(token))


C4 = "c4_owner_matilda_range"
C4_BASE = [
    "直近の窓(既定 40 分)の上端・下端・中心・平均実体を毎分計算する(上端・下端の既定は実体の端)。",
    "中心から「入りの離れ」(既定 2 × 平均実体)離れた位置で、上なら売り・下なら買いで建て、同じ向きの合図では前の段の終値から 1 × 平均実体 動くごとに 1 段足す(最大 7 段。持ち高 = 向き × 段数 ÷ 7)。",
    "利確(既定)は建値から按分した値幅(0.8 × 平均実体 ÷ 段数)。向きを持って 20 分たつか建値が中心より損の側なら線を中心まで緩め、40 分たつと時間成行で閉じる。",
    "幅 ÷ 終値が小さすぎる局面は建てず(幅の門)、窓の幅 ÷ 平均実体が 10 以上の一方向の動きの間は静観する(持ち高 0 からは入らず、反対向きは閉じ、同じ向きは持つ)。",
]
C4_SRC = [
    _card(C4, "「原文(逐語)」(オーナー由来。docs/STRATEGY_IDEAS.md 12〜20 行の O-1・O-2、OWNER_LOG L-018、docs/legacy/matilda_v52.py 122〜125 行のコメント)"),
    _card(C4, "「水準とその出所」の表(窓・入りの離れ・利確・段・時間成行・幅の門・静観の比)"),
    _card(C4, "「約定の模型」(足の終わりに出した持ち高を次の足の始値で成行約定、経費なし)と「測る期間」(2015-11-28T15:00Z〜2023-12-17T15:00Z)"),
]


def _single(card: str, title: str, description: list[str], sources: list[str], **extra) -> dict:
    return {"id": "", "title": title, "description": description, "sources": sources, "pattern": r"default", "axes": [], "prefix": "", **extra}


#: card theme = {card, title, summary, owner_origin, sources, instrument, instrument_source, strategies: [family]}.
#: family = {id, title, description (3 to 6 sentences), sources, pattern (a regex over the variant name; its named groups
#: are axis keys of CARD_AXES), axes (keys in display order), prefix (the start of a variant name this family holds: used to
#: place an excluded entry), default (the variant shown first)}.
CARD_THEMES: list[dict] = [
    {
        "card": "c1_xborder_mom", "owner_origin": False,
        "title": "Binance の大きな動きに bitFlyer が付いてくるか(今の paper bot の戦略)",
        "summary": "今の paper bot の戦略 xborder_momentum を研究のカードに移したもの。Binance の 30 分の値動きに従って bitFlyer FX_BTC_JPY を持つ。",
        "sources": [_card("c1_xborder_mom", "「原文(逐語)」S1〜S5 と「このカードを選んだ理由」")],
        "instrument": "FX_BTC_JPY",
        "instrument_source": _card("c1_xborder_mom", "「意図の地図」I-1(持つ銘柄 = bitFlyer FX_BTC_JPY)"),
        "strategies": [_single(
            "c1_xborder_mom", "Binance の大きな動きに bitFlyer が付いてくるか(今の paper bot の戦略)",
            ["持つのは bitFlyer の FX_BTC_JPY、信号は Binance BTCUSDT の 1 分足の終値(今の paper bot の戦略をそのままカードにした)。",
             "毎分、Binance の 30 本(30 分)前からの値動き(対数)を見る。",
             "値動きが +0.8% を超えれば買い(+1)、−0.8% を下回れば売り(−1)、絶対値が 0.05% 以下なら決済(0)、その間は前の足の持ち高のまま。",
             "足の終わりに出した持ち高を、次の bitFlyer の足の始値で成行約定したとみなす。経費は入れない。",
             "損切り 0.5%・ドテンしないこと・SFD の守りは bot の守りで、カードの外(意図の地図で射程外)。",
             "測る期間は 2017-08-17T15:00Z〜2023-12-17T15:00Z(日本時間の日の境にそろえた)。"],
            [_card("c1_xborder_mom", "「原文(逐語)」S1(on_candles の k・閾値・決済の帯)・S2(config.yaml の k 30・thr_pct 0.8・exit_pct 0.05)・S3(e = +1 / −1 / 0 / 前の足の e)"),
             _card("c1_xborder_mom", "「約定の模型」「測る期間」と「意図の地図」I-17〜I-19(射程外)")],
        )],
    },
    {
        "card": "c2_owner_xvenue_wick", "owner_origin": True,
        "title": "海外取引所のヒゲの後に bitFlyer で逆張り(カツオのヒゲ・取引所横断)",
        "summary": "オーナーの案 O-6「シグナルは外、執行は自市場」と O-3 カツオのヒゲの強さの区別。海外の足のヒゲで bitFlyer FX_BTC_JPY を逆張りで持つ。",
        "sources": [_card("c2_owner_xvenue_wick", "「原文(逐語)」(docs/STRATEGY_IDEAS.md 21〜37 行の O-3・O-3b・O-3c・O-6、OWNER_LOG L-023〜L-025・L-044・L-052・L-053 の逐語)")],
        "instrument": "FX_BTC_JPY",
        "instrument_source": _card("c2_owner_xvenue_wick", "「約定の模型」(次の bitFlyer の足の始値で約定)"),
        "strategies": [{
            "id": "", "title": "海外取引所のヒゲの後に bitFlyer で逆張り(カツオのヒゲ・取引所横断)",
            "description": [
                "シグナルは海外の取引所(Binance 現物・Binance USD-M 先物・BitMEX の 3 系列)の足、執行は bitFlyer FX_BTC_JPY(オーナーの O-6「シグナルは外、執行は自市場」)。",
                "海外の足(1・3・5・15・30・60 分。原典は 15 分)が閉じたとき、長い方のヒゲが「19 bp 以上かつ実体より長い」または「24 bp 以上」なら、下ヒゲで買い・上ヒゲで売り(逆張り)。",
                "上ヒゲ陰線・下ヒゲ陽線は強い(反対の持ち高があればドテン)、上ヒゲ陽線・下ヒゲ陰線は弱い(反対の持ち高は決済で止め、持ち高が無ければ新規に建てる)。",
                "持ち高 0 に戻すのは、シグナル足のヒゲ先端を、持ち高と反対の色でシグナルの無い足の終値が超えたとき(足の途中では見ない)。",
                "持ち高は −1 / 0 / +1 で、足の終わりに出した持ち高を次の bitFlyer の足の始値で成行約定したとみなす。経費は入れない。"],
            "sources": [_card("c2_owner_xvenue_wick", "「原文(逐語)」(STRATEGY_IDEAS 21〜37 行 O-3・O-6、OWNER_LOG L-024・L-025・L-044・L-052・L-053)"),
                        _card("c2_owner_xvenue_wick", "「意図の地図」の要点(入る条件・強弱・出る条件・保有中の判断)と「水準とその出所」(19 bp・24 bp・足の長さ)"),
                        _card("c2_owner_xvenue_wick", "「約定の模型」「変種と測る順」")],
            "pattern": r"(?P<c2_series>[a-z])_(?P<c2_foot>\d+)m", "axes": ["c2_series", "c2_foot"], "prefix": "", "default": "a_15m"}],
    },
    {
        "card": "c3_yen_premium_revert", "owner_origin": False,
        "title": "円の上乗せの戻り(bitFlyer と Binance × USDJPY の差が開いたあと)",
        "summary": "bitFlyer の価格と、Binance × USDJPY(円に直した海外の価格)の差(円の上乗せ)が直近の分布から開いたとき、戻る向きに bitFlyer を持つ。",
        "sources": [_card("c3_yen_premium_revert", "「原文(逐語)」(案 D1-D-21 の全欄と、第 3 版 §5-1・W4 の仕様 §1 の逐語)")],
        "instrument": "FX_BTC_JPY",
        "instrument_source": _card("c3_yen_premium_revert", "「意図の地図」I-1c(bitFlyer の価格 = FX_BTC_JPY の 1 分足)と I-6b(bitFlyer の脚だけを持つ)"),
        "strategies": [{
            "id": "", "title": "円の上乗せの戻り(bitFlyer と Binance × USDJPY の差が開いたあと)",
            "description": [
                "円の上乗せ = bitFlyer FX_BTC_JPY の価格と、Binance BTCUSDT × USDJPY(円に直した海外の価格)の比。",
                "直近の窓(1 時間・1 日・1 週の 3 変種)の中で、今の上乗せがどの位置(分位 q。0〜1)にあるかを見る。",
                "持ち高 e = 1 − 2q。上乗せが窓の上端なら −1(bitFlyer を売り)、下端なら +1(買い)、中央なら 0 で、戻る向きに持つ。",
                "窓が満ちるまでと、Binance の同じ分の行が無い足は 0。持つのは bitFlyer の脚だけで、海外の脚は持たない。",
                "足の終わりに出した持ち高を次の足の始値で成行約定したとみなす。経費は入れない。期間は 2017-08-17T15:00Z〜2022-12-31T15:00Z(USDJPY の置き場が 2022-12-31 まで)。"],
            "sources": [_card("c3_yen_premium_revert", "「原文(逐語)」の案 D1-D-21 と、第 3 版 §5-1 の逐語(上乗せ ≡ bitFlyer の価格 ÷(BTCUSD × USDJPY))"),
                        _card("c3_yen_premium_revert", "「水準とその出所」(窓の 3 変種・位置から持ち高への写し e = 1 − 2q)と「期待する向き」"),
                        _card("c3_yen_premium_revert", "「約定の模型」「測る期間」")],
            "pattern": r"(?P<c3_window>1h|1d|1w|[0-9a-z]+)", "axes": ["c3_window"], "prefix": ""}],
    },
    {
        "card": C4, "owner_origin": True,
        "title": "マチルダ: レンジの中心から離れて建て、中心近くで利確する",
        "summary": "オーナーの案 O-1「レンジ中心回帰グリッド(マチルダの戦略ロジック)」と O-2「レンジ性の判定器」。研究のカードとしては、部品の切り分け・水準の地図・指値の模型の 3 つの形で測っている。",
        "sources": [_card(C4, "「原文(逐語)」(docs/STRATEGY_IDEAS.md 12〜20 行の O-1・O-2、OWNER_LOG L-018、docs/legacy/matilda_v52.py 122〜125 行のコメント)")],
        "instrument": "FX_BTC_JPY",
        "instrument_source": _card(C4, "「水準とその出所」2019-09-04 の値段の節(bitFlyer FX_BTC_JPY の 1 分足)と limit_sim/SPEC.md §1(入力)"),
        "strategies": [
            {"id": "parts", "title": "マチルダ: 部品を 1 つずつ外した版(部品の切り分け)",
             "description": C4_BASE + ["この組は、4 つの部品(幅の門・静観の門・時間成行・段)を 1 つずつ外した版、一方向の動きの間も向きに入る版(follow)、4 つとも切った版(core)を、レンジの端(実体 / ヒゲ込み)別に並べる。"],
             "sources": C4_SRC + [f"{RUN_B2} の C4_KW(部品の名前と引数の対応)"],
             "pattern": r"(?P<c4_part>[a-z_]+?)_(?P<c4_range>body|wick)", "axes": ["c4_part", "c4_range"], "prefix": "", "default": "full_body"},
            {"id": "map", "title": "マチルダ: 水準の地図(足 × 窓 × 入りの離れ × 利確の形)",
             "description": C4_BASE + ["この組は、足(1・5 分)・窓(10〜160 分)・入りの離れ(1〜3 × 平均実体)・利確の形(4 通り)を替えた地図で、部品はすべて既定のまま(実体の端・全部品あり)。"],
             "sources": C4_SRC + [_card(C4, "「地図のための値の表の拡張」"), f"{RUN_B2} の C4_MAP・C4_TP(変種名 m_b<足>_w<窓>_e<離れ>_<利確> と利確の形)"],
             "pattern": r"m_b(?P<c4_bar>\d+)_w(?P<c4_win>\d+)_e(?P<c4_entry>\d+(?:\.\d+)?)_(?P<c4_tp>[a-z0-9]+)",
             "axes": ["c4_bar", "c4_win", "c4_entry", "c4_tp"], "prefix": "m_"},
            {"id": "limit", "title": "マチルダ: 指値の模型(v37 を 1 分足で指値として再現)",
             "description": [
                 "カードの口(持ち高を毎分返す形)は指値を表せないので、原典 v37 を 1 分足で指値として再現する別の模型(MatildaLimitSim)で測った版。",
                 "レンジの中心から入りの離れ(2 × 平均実体)の値段に指値を置き、約定は指値の値段そのもの(次の足の始値ではない)。",
                 "取引は、持ち高が 0 から離れて 0 に戻るまでを 1 件とする(段の損益の和)。建て・決済の時刻は足の終わりの時刻。",
                 "1 分足は高値と安値のどちらが先かを持たないので、1 本の足に入りと利確などが重なる足は「決まらない足」とし、損益の良い方の道(良い側)・悪い方の道(悪い側)の 2 通りで進める。",
                 "期間は 2015-11-28T15:00Z〜2023-12-17T15:00Z。損益は取引の値段から出した bp(SPEC §4)で、SPEC に経費の記載は無い。"],
             "sources": [_card(C4, "limit_sim/SPEC.md の §1〜§4(入力・指値の約定・決まらない足・損益)"),
                         "src/bot/research/matilda_limit_sim.py の docstring(1 本の足の中の扱い・決まらない足)", f"{W4_SCRIPTS}/c4_limit_run.py の --fill-side"],
             "pattern": r"limit_v37_(?P<c4_fill>good|bad)", "axes": ["c4_fill"], "prefix": "limit_"},
        ],
    },
    {
        "card": "c5_tokyo_fix_momentum", "owner_origin": False,
        "title": "東京仲値の前の値動きに追随する(日本時間の朝)",
        "summary": "為替の仲値が決まる前の値動きに追随する順張りを、bitFlyer FX_BTC_JPY を持つ形に移したカード。原文は 1 文だけ(案 #46)。",
        "sources": [_card("c5_tokyo_fix_momentum", "「原文(逐語)」(docs/STRATEGY_IDEAS.md 81 行の案 #46 と、第 5 版・第 3 版の逐語)")],
        "instrument": "FX_BTC_JPY",
        "instrument_source": _card("c5_tokyo_fix_momentum", "「意図の地図」I-4(bitFlyer FX_BTC_JPY の自分の値動きに移した)"),
        "strategies": [_single(
            "c5_tokyo_fix_momentum", "東京仲値の前の値動きに追随する(日本時間の朝)",
            ["原文は「仲値決定前の値動きに追随する順張りが機能するか」の 1 文だけ。原文は為替が対象で、このカードは bitFlyer FX_BTC_JPY の自分の値動きに移した(代理)。",
             "日本時間の日の境 0 時の足の始値を起点に、そこから今までに上がっていれば買い(+1)、下がっていれば売り(−1)、同じなら 0 を毎足出し直す。",
             "持つのは日本時間の月〜金の 0 時から 9 時 55 分(仲値の決定の時刻)までで、9 時 55 分に終わる足で 0 に戻す。仲値の後と土日は持たない(祝日は除けていない)。",
             "足の終わりに出した持ち高を次の足の始値で成行約定したとみなす。経費は入れない。",
             "期間は 2015-11-28T15:00Z〜2023-12-17T15:00Z。"],
            [_card("c5_tokyo_fix_momentum", "「原文(逐語)」(案 #46)と「意図の地図」I-1a〜I-4"),
             _card("c5_tokyo_fix_momentum", "「水準とその出所」(仲値の時刻 9 時 55 分・日の起点・平日)と「約定の模型」「測る期間」")],
        )],
    },
    {
        "card": "c6_weekend_gap_revert", "owner_origin": False,
        "title": "週末ギャップの 1 時間平均回帰",
        "summary": "週明けの価格ギャップが最初の 1 時間で縮む性質を、bitFlyer FX_BTC_JPY を持つ形で測るカード。原文は 1 文だけ(案 #45)で、ギャップの定義を 2 変種にした。",
        "sources": [_card("c6_weekend_gap_revert", "「原文(逐語)」(docs/STRATEGY_IDEAS.md 80 行の案 #45)と「「週末」「ギャップ」が何を指すか」")],
        "instrument": "FX_BTC_JPY",
        "instrument_source": _card("c6_weekend_gap_revert", "「使うデータと遅れ」の表(bitFlyer FX_BTC_JPY 1 分足 = 持つ銘柄の足。USDJPY は参照)と「意図の地図」I-6"),
        "strategies": [{
            "id": "", "title": "週末ギャップの 1 時間平均回帰",
            "description": [
                "原文は「週明けの価格ギャップが、最初の 1 時間で平均的に縮小(回帰)する性質を利用できるか」の 1 文だけ。",
                "bitFlyer FX_BTC_JPY は週末も取引されるので、週末に閉まる USDJPY の市場を時計にして週明けの行を見つける(代理)。",
                "ギャップが上に開いていれば売り、下なら買い(縮む向き)で、持つのは週明けの行の 1 分後から 1 時間後までの 59 分だけ。",
                "ギャップの定義が原文から決まらないので 2 変種にした。「USDJPY の窓」は USDJPY の週明けの窓、「BTC の動き」は為替が閉まっていた間の FX_BTC_JPY の値動き。どちらも持つのは FX_BTC_JPY。",
                "足の終わりに出した持ち高を次の足の始値で成行約定したとみなす。経費は入れない。期間は 2017-08-01T15:00Z〜2022-12-31T15:00Z。"],
            "sources": [_card("c6_weekend_gap_revert", "「原文(逐語)」(案 #45)と「「週末」「ギャップ」が何を指すか」"),
                        _card("c6_weekend_gap_revert", "「期待する向き」「水準とその出所」(持つ長さ・週の境・週明けの行)と「約定の模型」「測る期間」")],
            "pattern": r"(?P<c6_gap>usdjpy|btc|[a-z0-9]+)", "axes": ["c6_gap"], "prefix": ""}],
    },
    {
        "card": "c7_barrier_race", "owner_origin": False,
        "title": "バリアレース逆張り(一定幅動いたら反対側へ)",
        "summary": "価格が一定幅動いたあと、同方向へ続くか反対へ戻るかのどちらが優勢かを、bitFlyer FX_BTC_JPY を逆張りで持って測るカード。原文は 1 文だけ(案 #48)。",
        "sources": [_card("c7_barrier_race", "「原文(逐語)」(docs/STRATEGY_IDEAS.md 82 行の案 #48)")],
        "instrument": "FX_BTC_JPY",
        "instrument_source": _card("c7_barrier_race", "「意図の地図」I-6(対象の価格は bitFlyer FX_BTC_JPY)"),
        "strategies": [{
            "id": "", "title": "バリアレース逆張り(一定幅動いたら反対側へ)",
            "description": [
                "原文は「価格が一定幅動いたときに、その後さらに同方向へ動く(継続)か反対方向へ戻る(反転)かのどちらが優勢か」の 1 文だけ。",
                "幅は、直近の窓(1 時間・1 日・1 週の 3 変種)の 1 分ごとの対数の値動きの 2 乗の和の平方根で、レースの始まりごとに決め直す。",
                "起点から上の線と下の線のどちらに先に終値が当たるかを競わせる(当たりは終値で >= / <=)。",
                "上の線に当たれば売り、下の線に当たれば買い(逆張り)で、次の当たりまで持つ。当たった足の終値を新しい起点にして次のレースを始める。最初の当たりまでは 0。",
                "足の終わりに出した持ち高を次の足の始値で成行約定したとみなす。経費は入れない。"],
            "sources": [_card("c7_barrier_race", "「原文(逐語)」(案 #48)と「意図の地図」I-1a〜I-5"),
                        _card("c7_barrier_race", "「水準とその出所」(幅の窓・幅 w の式・当たりの判定)と「約定の模型」")],
            "pattern": r"(?P<c7_window>1h|1d|1w|[0-9a-z]+)", "axes": ["c7_window"], "prefix": ""}],
    },
    {
        "card": "c8_session_mean_revert", "owner_origin": False,
        "title": "セッション内の平均回帰(日本時間の日など)",
        "summary": "セッション内の価格が平均的な水準へ戻る性質を、bitFlyer FX_BTC_JPY を持って測るカード。原文は 1 文だけ(案 #49)で、セッションの区切りを 2 変種にした。",
        "sources": [_card("c8_session_mean_revert", "「原文(逐語)」(docs/STRATEGY_IDEAS.md 83 行の案 #49)と「「セッション」が何を指すか」")],
        "instrument": "FX_BTC_JPY",
        "instrument_source": _card("c8_session_mean_revert", "「意図の地図」I-6(対象の「価格」は bitFlyer FX_BTC_JPY)"),
        "strategies": [{
            "id": "", "title": "セッション内の平均回帰(日本時間の日など)",
            "description": [
                "原文は「セッション内の価格が平均的な水準へ回帰する性質を利用できるか」の 1 文だけ。bitFlyer に立会の区切りは無いので、セッションを時計で決めた 2 変種にした(日本時間の日 / bitFlyer の保守の始まりから翌日)。",
                "水準 = セッションの始まりから今までの、約定のあった足の終値の算術平均。",
                "終値が平均より上なら売り、下なら買い(平均へ向かう向き。±1)、ちょうど平均なら 0 を毎足出し直す。",
                "セッションの最初の足と最後の足は 0 で、セッションをまたいで持たない。",
                "足の終わりに出した持ち高を次の足の始値で成行約定したとみなす。経費は入れない。"],
            "sources": [_card("c8_session_mean_revert", "「原文(逐語)」(案 #49)と「「セッション」が何を指すか」"),
                        _card("c8_session_mean_revert", "「意図の地図」I-1〜I-5・「水準とその出所」・「約定の模型」")],
            "pattern": r"(?P<c8_session>jst_day|bf_maint|[a-z0-9_]+)", "axes": ["c8_session"], "prefix": ""}],
    },
    {
        "card": "c9_liquidation_cascade", "owner_origin": True,
        "title": "清算の連鎖の直後の bitFlyer の動き(測定なし)",
        "summary": "海外の清算の直後の bitFlyer の動きを見るカード。まだ測定が無く(文書のみ)、このタブに出す結果は無い。",
        "sources": [_card("c9_liquidation_cascade", "「原文(逐語)」の原文 A(第 5 版 段 3-B の表の行)と原文 B(docs/STRATEGY_IDEAS.md 29〜31 行 O-3c。オーナー由来)")],
        "instrument": None, "instrument_source": "",
        "strategies": [_single(
            "c9_liquidation_cascade", "清算の連鎖の直後の bitFlyer の動き(測定なし)",
            ["計画 第 5 版 段 3-B の「清算の連鎖」の行を 1 枚にしたカードで、問いは「海外の清算の直後の bitFlyer の動き」。",
             "オーナーの O-3c「強制決済フローの観測」(ロスカットの連鎖そのものを観測できれば、ヒゲより精確に判定できるか)を受けている。",
             "測定がまだ無い(文書のみ)ので、この画面に出す取引・損益は無い。"],
            [_card("c9_liquidation_cascade", "「原文(逐語)」の原文 A・原文 B(オーナー由来の O-3c。OWNER_LOG L-044・L-025 の逐語を含む)")],
        )],
    },
]


def card_theme(card: str) -> Optional[dict]:
    for ct in CARD_THEMES:
        if ct["card"] == card:
            return ct
    return None


def card_families(ct: dict) -> list[dict]:
    """The families of a card theme with their ids filled in (a single-family card's id is the card's own)."""
    sts = ct["strategies"]
    return [{**s, "id": (s["id"] or "main")} for s in sts]


def card_family_of(ct: dict, variant: str) -> tuple[Optional[dict], dict]:
    """(family, {axis key: token}) of a variant name by the first family whose pattern splits the whole name; (None, {})
    when none does."""
    import re  # noqa: PLC0415
    for fam in card_families(ct):
        m = re.fullmatch(fam["pattern"], variant)
        if m:
            return fam, {k: v for k, v in m.groupdict().items() if v is not None}
    return None, {}
