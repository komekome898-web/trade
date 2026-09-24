"""Reproduction of candidate 52 QuantConnect LEAN: the data path only (round r6-3).

Minimal rewrite, in Python, of the part of LEAN that takes typed market data
from several subscriptions, synchronises them by time and hands the
algorithm one `Slice` per time step. Nothing is added to and nothing is
weakened from the primary source; what is not reproduced (orders, fills,
fees, portfolio, scheduled events, history requests) is absent here, and the
adapter reports those scenes as having no result.

Primary source: https://github.com/QuantConnect/Lean at commit
856327ff33869cba98393781000c4ab1d2af423d (read 2026-09-24 from a blobless
clone, read only; nothing of it was run). Each piece below names the file
and lines it rewrites.

This file is the reproduced target's code (run_battery.py places it for the
target `repro_lean52`); the scene-set side of the reproduction is
`opponents/repro_lean52.py`.
"""
from __future__ import annotations

# Common/Time.cs 145: EpochTime = new DateTime(1970, 1, 1, 0, 0, 0, 0). A .NET
# DateTime counts 100-ns ticks; this rewrite keeps a DateTime as its tick count
# since the Unix epoch (an int), which is exactly what DateTime arithmetic keeps.
TICKS_PER_SECOND = 10_000_000


def unix_ns_to_datetime(ns: int) -> int:
    """Common/Time.cs 274-288 UnixNanosecondTimeStampToDateTime:
    `var ticks = unixTimeStamp / 100; time = EpochTime.AddTicks(ticks);`
    (C# long division truncates toward zero)."""
    q = abs(int(ns)) // 100
    return q if ns >= 0 else -q


def datetime_to_unix_ns(ticks: int) -> int:
    """Common/Time.cs 333-340 DateTimeToUnixTimeStampNanoseconds:
    `(time - new DateTime(1970, 1, 1, 0, 0, 0, 0)).Ticks * 100`."""
    return int(ticks) * 100


class MarketDataType:
    """Common/Global.cs MarketDataType (the members this rewrite uses)."""
    Base, TradeBar, Tick, Auxiliary = "Base", "TradeBar", "Tick", "Auxiliary"


class TickType:
    Trade, Quote = "Trade", "Quote"


class BaseData:
    """Common/Data/BaseData.cs: Time (86), EndTime = Time unless overridden
    (96-100), Symbol, Value, DataType."""

    def __init__(self) -> None:
        self.Time = 0
        self.Symbol = ""
        self.Value = 0.0
        self.DataType = MarketDataType.Base

    @property
    def EndTime(self) -> int:
        return self.Time


class TradeBar(BaseData):
    """Common/Data/Market/TradeBar.cs 170-184 TradeBar(time, symbol, open, high,
    low, close, volume, period = null): `Period = period ?? Time.OneMinute`,
    `Value = close`; EndTime = Time + Period (106-113)."""

    ONE_MINUTE = 60 * TICKS_PER_SECOND  # Common/Time.cs Time.OneMinute

    def __init__(self, time: int, symbol: str, open_: float, high: float, low: float, close: float,
                 volume: float, period: int | None = None) -> None:
        super().__init__()
        self.Time, self.Symbol, self.Value = time, symbol, close
        self.Open, self.High, self.Low, self.Close, self.Volume = open_, high, low, close, volume
        self.Period = self.ONE_MINUTE if period is None else period
        self.DataType = MarketDataType.TradeBar

    @property
    def EndTime(self) -> int:
        return self.Time + self.Period


class Tick(BaseData):
    """Common/Data/Market/Tick.cs 283-294 Tick(time, symbol, saleCondition,
    exchange, quantity, price): a trade tick (`TickType = TickType.Trade`,
    `Value = price`). The class has no aggressor-side field (Tick.cs 40-172:
    TickType, Quantity, Exchange, SaleCondition, Suspicious, BidPrice,
    AskPrice, BidSize, AskSize, LastPrice)."""

    def __init__(self, time: int, symbol: str, sale_condition: str, exchange: str, quantity: float, price: float) -> None:
        super().__init__()
        self.Value, self.Time, self.Symbol = price, time, symbol
        self.DataType = MarketDataType.Tick
        self.TickType = TickType.Trade
        self.Quantity, self.Exchange, self.SaleCondition = quantity, exchange, sale_condition
        self.Suspicious = False

    @property
    def Price(self) -> float:  # BaseData.cs: `public virtual decimal Price => Value`
        return self.Value


class MarginInterestRate(BaseData):
    """Common/Data/Market/MarginInterestRate.cs: the funding-rate data
    (`InterestRate = Value = rate`, Reader 58-68), `DataType =
    MarketDataType.Auxiliary` (constructor 38-41), time zone UTC."""

    def __init__(self) -> None:
        super().__init__()
        self.InterestRate = 0.0
        self.DataType = MarketDataType.Auxiliary


class Subscription:
    """Engine/DataFeeds/Subscription.cs: an enumerator over one data source,
    in the source's order; `Current` holds SubscriptionData whose EmitTimeUtc
    is `ConvertToUtc(data.EndTime)` (Engine/DataFeeds/SubscriptionData.cs 73;
    every source here is UTC)."""

    def __init__(self, data: list[BaseData]) -> None:
        self._it = iter(data)
        self.Current: BaseData | None = None
        self.EndOfStream = False

    def MoveNext(self) -> bool:
        self.Current = next(self._it, None)
        if self.Current is None:
            self.EndOfStream = True
            return False
        return True

    @staticmethod
    def EmitTimeUtc(data: BaseData) -> int:
        return data.EndTime


class SubscriptionFrontierTimeProvider:
    """Engine/DataFeeds/SubscriptionFrontierTimeProvider.cs 63-96 GetUtcNow /
    UpdateCurrentTime: the earliest EmitTimeUtc over the subscriptions'
    current data (priming a new subscription with MoveNext), and the frontier
    never goes back: `_utcNow = new DateTime(Math.Max(earlyBirdTicks, _utcNow.Ticks))`."""

    MAX = 3_155_378_975_999_999_999  # DateTime.MaxValue.Ticks

    def __init__(self, utc_now: int, subscriptions: list[Subscription]) -> None:
        self._utc_now, self._subs = utc_now, subscriptions

    def GetUtcNow(self) -> int:
        early = self.MAX
        for s in self._subs:
            if s.Current is None and not s.EndOfStream:
                s.MoveNext()
            if s.Current is not None:
                early = min(early, Subscription.EmitTimeUtc(s.Current))
        if early != self.MAX:
            self._utc_now = max(early, self._utc_now)
        return self._utc_now


class DataFeedPacket:
    def __init__(self, symbol: str) -> None:
        self.Symbol, self.Data = symbol, []


class TradeBars(dict):
    """Common/Data/Market/TradeBars.cs: DataDictionary<TradeBar> keyed by symbol."""


class Ticks(dict):
    """Common/Data/Market/Ticks.cs 25: DataDictionary<List<Tick>> keyed by symbol."""


class MarginInterestRates(dict):
    """Common/Data/Market/MarginInterestRates.cs: DataDictionary<MarginInterestRate>."""


class Slice:
    """Common/Data/Slice.cs: Time (62), HasData (78), Bars (86), Ticks (102),
    MarginInterestRates (166); the constructor keeps the collections the
    factory built (301)."""

    def __init__(self, time: int, all_data: list[BaseData], trade_bars: TradeBars, ticks: Ticks,
                 margin_interest_rates: MarginInterestRates, utc_time: int, has_data: bool) -> None:
        self.Time, self.UtcTime = time, utc_time
        self._data = all_data
        self.Bars, self.Ticks, self.MarginInterestRates = trade_bars, ticks, margin_interest_rates
        self.HasData = has_data


def time_slice_create(utc_time: int, data: list[DataFeedPacket]) -> Slice:
    """Engine/DataFeeds/TimeSliceFactory.cs Create (95-392), the parts for these
    types: every datum goes to allDataForAlgorithm (184); a Tick is appended
    to ticks[symbol] (199-205); a TradeBar replaces tradeBars[symbol] only when
    none is there or the existing one has a longer Period (207-223); a
    MarginInterestRate (Auxiliary) is stored as marginInterestRates[symbol]
    (365-372); the Slice has data when allDataForAlgorithm is not empty (389).
    The algorithm's time zone is UTC here (algorithmTime = utcDateTime)."""
    all_data: list[BaseData] = []
    bars, ticks, rates = TradeBars(), Ticks(), MarginInterestRates()
    for packet in data:
        for d in packet.Data:
            all_data.append(d)
            if d.DataType != MarketDataType.Auxiliary:
                if d.DataType == MarketDataType.Tick:
                    ticks.setdefault(d.Symbol, []).append(d)
                elif d.DataType == MarketDataType.TradeBar:
                    old = bars.get(d.Symbol)
                    if old is None or old.Period > d.Period:
                        bars[d.Symbol] = d
            elif isinstance(d, MarginInterestRate):
                rates[packet.Symbol] = d
    return Slice(utc_time, all_data, bars, ticks, rates, utc_time, len(all_data) > 0)


def sync(subscriptions: list[Subscription], symbols: list[str], start_utc: int):
    """Engine/DataFeeds/SubscriptionSynchronizer.cs Sync (88-262): take the
    frontier (101), then for each subscription in order (109) move every
    datum with EmitTimeUtc <= frontier into that subscription's packet
    (129-167), then create the time slice (250). Stops when every
    subscription is at its end (the engine stops when the feed ends)."""
    frontier = SubscriptionFrontierTimeProvider(start_utc, subscriptions)
    while True:
        utc = frontier.GetUtcNow()
        data = []
        for sub, sym in zip(subscriptions, symbols):
            if sub.EndOfStream:
                continue
            if sub.Current is None and not sub.MoveNext():
                continue
            packet = None
            while sub.Current is not None and Subscription.EmitTimeUtc(sub.Current) <= utc:
                if packet is None:
                    packet = DataFeedPacket(sym)
                packet.Data.append(sub.Current)
                if not sub.MoveNext():
                    break
            if packet is not None and packet.Data:
                data.append(packet)
        if not data and all(s.EndOfStream for s in subscriptions):
            return
        yield time_slice_create(utc, data)


class QCAlgorithm:
    """Algorithm/QCAlgorithm.cs: the user's algorithm overrides OnData(Slice)
    (Common/Interfaces/IAlgorithm.cs 521); `Time` is the algorithm's clock,
    set by SetDateTime."""

    def __init__(self) -> None:
        self.UtcTime = 0

    def SetDateTime(self, utc: int) -> None:
        self.UtcTime = utc

    def OnData(self, slice_: Slice) -> None:  # noqa: N802 - LEAN's name
        pass


def run(algorithm: QCAlgorithm, sources: list[tuple[str, list[BaseData]]]) -> None:
    """Engine/AlgorithmManager.cs Run: for each time slice of the feed (191),
    `algorithm.SetDateTime(time)` (244), then
    `if (timeSlice.Slice.HasData) algorithm.OnData(algorithm.CurrentSlice)` (582-586)."""
    subs = [Subscription(list(data)) for _, data in sources]
    for ts in sync(subs, [sym for sym, _ in sources], 0):
        algorithm.SetDateTime(ts.UtcTime)
        if ts.HasData:
            algorithm.OnData(ts)
