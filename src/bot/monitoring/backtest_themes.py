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
