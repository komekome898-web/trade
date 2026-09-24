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

Round r7-1 (critic i0-r6-04): a rewritten statement is rewritten together
with every condition of the source that encloses it. Each function below
lists the conditions of the cited range: the ones rewritten (with their
lines), and the ones not rewritten with the source lines that show they
cannot hold for the scenes' subscriptions. The source files were read at
the same commit with `git show` (a blobless clone; nothing of it was run).
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


class SecurityType:
    """Common/Global.cs SecurityType; only the member the scenes use."""
    CryptoFuture = "CryptoFuture"


# Common/Global.cs 512-528 `public enum TickType { Trade, Quote, OpenInterest }`: the
# enum's numeric order is what SubscriptionCollection.SortSubscriptions orders by.
TICK_TYPE_RANK = {TickType.Trade: 0, TickType.Quote: 1, "OpenInterest": 2}


class SubscriptionDataConfig:
    """Common/Data/SubscriptionDataConfig.cs: Type, Symbol, TickType,
    SecurityType (of the symbol), IsInternalFeed (82: set from the
    constructor's `isInternalFeed`, 207 / 227), IsCustomData."""

    def __init__(self, type_: type, symbol: str, tick_type: str, security_type: str, is_internal_feed: bool,
                 is_custom_data: bool = False, fill_forward: bool = False) -> None:
        self.Type, self.Symbol, self.TickType, self.SecurityType = type_, symbol, tick_type, security_type
        self.IsInternalFeed, self.IsCustomData = is_internal_feed, is_custom_data
        # 72 / 242: `FillDataForward = resolution == Resolution.Tick ? false : fillForward`. The scene set adds
        # the security with the public argument fillForward: false (QCAlgorithm.cs 2621 AddCryptoFuture(...,
        # bool fillForward = true, ...)); the feed adds a FillForwardEnumerator only when it is true and the
        # resolution is not Tick (FileSystemDataFeed.cs 239, 274-277), so no fill-forward data are made and
        # that enumerator is not rewritten here.
        self.FillDataForward = fill_forward


def data_manager_add(symbol: str, security_type: str, data_types: list[tuple[type, str]],
                     subscription_data_types_given: bool = False, is_internal_feed: bool = False) -> list[SubscriptionDataConfig]:
    """Engine/DataFeeds/DataManager.cs 602-690 Add(...): one config per (data
    type, tick type), with the internal flag of 720-721:
    `subscriptionDataTypes == null && tickType == TickType.OpenInterest || isInternalFeed`.
    A user's CryptoFuture goes through QCAlgorithm.AddCryptoFuture
    (QCAlgorithm.cs 2621-2624) -> AddSecurity<T> (3069-3083), which calls
    SubscriptionDataConfigService.Add without the `isInternalFeed` and
    `subscriptionDataTypes` arguments: their defaults are
    `false` and `null` (ISubscriptionDataConfigService.cs 53-64, DataManager.cs
    602-613); the data types then come from LookupSubscriptionConfigDataTypes
    (763-773: the security type's tick types, Trade and Quote for a
    CryptoFuture, SubscriptionManager.cs 361, and a MarginInterestRate with
    TickType.Quote for a CryptoFuture, 770-773)."""
    return [SubscriptionDataConfig(t, symbol, tt, security_type,
                                   (not subscription_data_types_given and tt == "OpenInterest") or is_internal_feed,
                                   fill_forward=False)
            for t, tt in data_types]


class Subscription:
    """Engine/DataFeeds/Subscription.cs: an enumerator over one data source,
    in the source's order; `Current` holds SubscriptionData whose EmitTimeUtc
    is `ConvertToUtc(data.EndTime)` (Engine/DataFeeds/SubscriptionData.cs 73;
    every source here is UTC). `Configuration`, `UtcStartTime`,
    `RemovedFromUniverse` and `IsUniverseSelectionSubscription` are the
    members the synchroniser and the frontier read (Subscription.cs 87 / 118
    `IsUniverseSelectionSubscription = subscriptionRequest.IsUniverseSubscription`,
    92 / 122 `UtcStartTime = subscriptionRequest.StartTimeUtc`, 102 / 125 / 194
    RemovedFromUniverse, set only by MarkAsRemovedFromUniverse); the scenes'
    subscriptions are security data subscriptions (not a universe's), started
    at the start time, never removed."""

    def __init__(self, data: list[BaseData], configuration: SubscriptionDataConfig | None = None,
                 utc_start_time: int = 0) -> None:
        self._it = iter(data)
        self.Current: BaseData | None = None
        self.EndOfStream = False
        self.Configuration = configuration
        self.UtcStartTime = utc_start_time
        self.RemovedFromUniverse = False
        self.IsUniverseSelectionSubscription = False

    def MoveNext(self) -> bool:
        self.Current = next(self._it, None)
        if self.Current is None:
            self.EndOfStream = True
            return False
        return True

    @staticmethod
    def EmitTimeUtc(data: BaseData) -> int:
        return data.EndTime


def sort_subscriptions(subscriptions: list[Subscription]) -> list[Subscription]:
    """Engine/DataFeeds/SubscriptionCollection.cs 123-126 (GetEnumerator calls
    SortSubscriptions) and 213-227:
    `_subscriptions.Select(x => x.Value).OrderBy(x => x.Configuration.SecurityType)
    .ThenBy(x => x.Configuration.TickType).ThenBy(x => x.Configuration.Symbol).ToList()`.
    LINQ's OrderBy is stable, so subscriptions with the same key keep the
    order of `_subscriptions` (a ConcurrentDictionary), which the source does
    not fix: the caller passes them in one of its possible orders."""
    return sorted(subscriptions, key=lambda s: (s.Configuration.SecurityType, TICK_TYPE_RANK[s.Configuration.TickType],
                                                s.Configuration.Symbol))


class SubscriptionFrontierTimeProvider:
    """Engine/DataFeeds/SubscriptionFrontierTimeProvider.cs 47-96 GetUtcNow /
    UpdateCurrentTime: the earliest EmitTimeUtc over the subscriptions'
    current data, and the frontier never goes back:
    `_utcNow = new DateTime(Math.Max(earlyBirdTicks, _utcNow.Ticks))`.
    Conditions of 63-73 (when to MoveNext a subscription without current
    data), rewritten: `Current == null && !IsUniverseSelectionSubscription &&
    UtcStartTime == _utcNow || Current == null && IsUniverseSelectionSubscription`."""

    MAX = 3_155_378_975_999_999_999  # DateTime.MaxValue.Ticks

    def __init__(self, utc_now: int, subscriptions: list[Subscription]) -> None:
        self._utc_now, self._subs = utc_now, subscriptions

    def GetUtcNow(self) -> int:
        early = self.MAX
        for s in self._subs:
            if (s.Current is None and not s.IsUniverseSelectionSubscription and s.UtcStartTime == self._utc_now) or \
                    (s.Current is None and s.IsUniverseSelectionSubscription):
                s.MoveNext()
            if s.Current is not None:
                early = min(early, Subscription.EmitTimeUtc(s.Current))
        if early != self.MAX:
            self._utc_now = max(early, self._utc_now)
        return self._utc_now


class DataFeedPacket:
    """Engine/DataFeeds/DataFeedPacket.cs: the subscription's configuration,
    its data of this time step, and IsSubscriptionRemoved (from the
    subscription's RemovedFromUniverse, SubscriptionSynchronizer.cs 134-139)."""

    def __init__(self, configuration: SubscriptionDataConfig, is_subscription_removed: bool = False) -> None:
        self.Configuration = configuration
        self.Symbol = configuration.Symbol
        self.IsSubscriptionRemoved = is_subscription_removed
        self.Data: list[BaseData] = []


class TradeBars(dict):
    """Common/Data/Market/TradeBars.cs: DataDictionary<TradeBar> keyed by symbol."""


class Ticks(dict):
    """Common/Data/Market/Ticks.cs 25: DataDictionary<List<Tick>> keyed by symbol."""


class MarginInterestRates(dict):
    """Common/Data/Market/MarginInterestRates.cs: DataDictionary<MarginInterestRate>."""


class Slice:
    """Common/Data/Slice.cs: Time (62), AllData (57, set from the factory's
    allDataForAlgorithm, 305), HasData (78), Bars (86), Ticks (102),
    MarginInterestRates (166); the constructor keeps the collections the
    factory built (301)."""

    def __init__(self, time: int, all_data: list[BaseData], trade_bars: TradeBars, ticks: Ticks,
                 margin_interest_rates: MarginInterestRates, utc_time: int, has_data: bool) -> None:
        self.Time, self.UtcTime = time, utc_time
        self.AllData = all_data
        self.Bars, self.Ticks, self.MarginInterestRates = trade_bars, ticks, margin_interest_rates
        self.HasData = has_data


def time_slice_create(utc_time: int, data: list[DataFeedPacket]) -> Slice:
    """Engine/DataFeeds/TimeSliceFactory.cs Create (95-392), for the types
    TradeBar, Tick and MarginInterestRate. The algorithm's time zone is UTC
    here (algorithmTime = utcDateTime).

    Conditions of the range, rewritten (round r7-1):
      * 140-143 `if (packet.IsSubscriptionRemoved) continue;`
      * 148 `if (list.Count == 0) continue;`
      * 181-185 `if (!packet.Configuration.IsInternalFeed) allDataForAlgorithm.Add(baseData);`
      * 190 `if (baseData.DataType != MarketDataType.Auxiliary)` and inside it
        194 `if (!packet.Configuration.IsInternalFeed)` around the Ticks (199-205)
        and TradeBars (207-223) dictionaries;
      * 329 `else if ((delisting = baseData as Delisting) != null || !packet.Configuration.IsInternalFeed)`
        around the auxiliary dictionaries, of which MarginInterestRates (365-372);
      * 389 the Slice has data when allDataForAlgorithm is not empty.
    Conditions not rewritten, and why they cannot hold for the scenes:
      * 151-163 a packet holding one BaseDataCollection (universe data; the
        lines only count data): the scenes' subscriptions carry TradeBar / Tick /
        MarginInterestRate only;
      * 165-173 custom data (`IsCustomData`): the scenes' configs are not custom
        (DataManager.Add's `isCustomData` default false, 609);
      * 225-258 the QuoteBar, OptionChain and FuturesChain cases and 268-311 the
        option and futures chains: no such data or security; 260-265 the
        consolidator update (not in the Slice);
      * 316-317 a suspicious tick skips the rest of the datum's steps, after it
        is already in allDataForAlgorithm and Ticks (184, 199-205): the Slice
        is the same; 322-325 the option-underlying update (not in the Slice);
      * 331-363 delistings, dividends, splits, symbol changes: no such data;
      * 375-386 the security and consolidator updates (not in the Slice)."""
    all_data: list[BaseData] = []
    bars, ticks, rates = TradeBars(), Ticks(), MarginInterestRates()
    for packet in data:
        if packet.IsSubscriptionRemoved:
            continue
        if len(packet.Data) == 0:
            continue
        for d in packet.Data:
            if not packet.Configuration.IsInternalFeed:
                all_data.append(d)
            if d.DataType != MarketDataType.Auxiliary:
                if not packet.Configuration.IsInternalFeed:
                    if d.DataType == MarketDataType.Tick:
                        ticks.setdefault(d.Symbol, []).append(d)
                    elif d.DataType == MarketDataType.TradeBar:
                        old = bars.get(d.Symbol)
                        if old is None or old.Period > d.Period:
                            bars[d.Symbol] = d
            elif not packet.Configuration.IsInternalFeed:  # 329: a Delisting also passes; the scenes have none
                if isinstance(d, MarginInterestRate):
                    rates[packet.Configuration.Symbol] = d
    return Slice(utc_time, all_data, bars, ticks, rates, utc_time, len(all_data) > 0)


def sync(subscriptions: list[Subscription], start_utc: int):
    """Engine/DataFeeds/SubscriptionSynchronizer.cs Sync (88-262): take the
    frontier (101), then for each subscription in the collection's order
    (109; the collection enumerates them sorted, sort_subscriptions) move
    every datum with EmitTimeUtc <= frontier into that subscription's packet
    (129-167; the packet carries the subscription's RemovedFromUniverse, 134-139),
    keep packets with data (170-175), then create the time slice
    (250). Stops when every subscription is at its end (the engine stops when
    the feed ends).
    Conditions rewritten: 111-115 a subscription at its end is skipped;
    118-125 priming with MoveNext; 129 the frontier test; 170 `packet?.Count > 0`;
    173 `!subscription.IsUniverseSelectionSubscription`.
    Not rewritten, and why they cannot hold for the scenes: 149-160 a
    Delisting (no such data); 177-200 and 204-221 universe subscriptions (the
    scenes' subscriptions are not a universe's); 225-248 universe selection
    and pending internal feeds (no universe; the do-while runs once)."""
    subscriptions = sort_subscriptions(subscriptions)
    frontier = SubscriptionFrontierTimeProvider(start_utc, subscriptions)
    while True:
        utc = frontier.GetUtcNow()
        data = []
        for sub in subscriptions:
            if sub.EndOfStream:
                continue
            if sub.Current is None:
                if not sub.MoveNext():
                    continue
            packet = None
            while sub.Current is not None and Subscription.EmitTimeUtc(sub.Current) <= utc:
                if packet is None:
                    packet = DataFeedPacket(sub.Configuration, sub.RemovedFromUniverse)
                packet.Data.append(sub.Current)
                if not sub.MoveNext():
                    break
            if packet is not None and len(packet.Data) > 0 and not sub.IsUniverseSelectionSubscription:
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


def run(algorithm: QCAlgorithm, subscriptions: list[Subscription]) -> None:
    """Engine/AlgorithmManager.cs Run: for each time slice of the feed (191),
    `algorithm.SetDateTime(time)` (244), then
    `if (timeSlice.Slice.HasData) algorithm.OnData(algorithm.CurrentSlice)` (582-586).
    Conditions not rewritten, and why they cannot hold for the scenes: 197-201
    and 360-369 the algorithm's status is not Running / a runtime error (the
    scenes' algorithm only records); 204 cancellation (none); 216 the
    portfolio value <= 0 in a backtest (the scenes place no order; LEAN's
    default cash is not zero); 247 a time pulse (emitted only around universe
    selection, SubscriptionSynchronizer.cs 225-229)."""
    for ts in sync(subscriptions, 0):
        algorithm.SetDateTime(ts.UtcTime)
        if ts.HasData:
            algorithm.OnData(ts)
