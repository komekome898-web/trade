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

Round r8-1 (critic i0-r7-03, positive definition A): the rewrite now starts
at the user's public entry. The algorithm's Initialize calls
`QCAlgorithm.AddCryptoFuture(ticker, resolution, market, fillForward,
leverage)`; the data types of the subscriptions come out of LEAN's own
lookup from the resolution (`DataManager.Add` -> `LookupSubscriptionConfigDataTypes`
-> `LeanData.GetDataType`), the configs go into the user-defined universe
at the end of the time step, and one subscription is made per config by the
universe selection. The scene set no longer builds subscriptions from the
scene's event types. Each function below names the lines it rewrites.
Read on 2026-09-24 for this round (same commit, `git show`):
Common/Util/LeanData.cs, Common/Data/BaseData.cs, Common/Data/Market/
{Tick,TradeBar,MarginInterestRate}.cs, Common/Extensions.cs,
Algorithm/QCAlgorithm.Universe.cs, Common/Data/UniverseSelection/
{UserDefinedUniverse,Universe}.cs, Engine/DataFeeds/UniverseSelection.cs.
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


class Resolution:
    """Common/Global.cs 566-592 `public enum Resolution { Tick, Second, Minute, Hour, Daily }`."""
    Tick, Second, Minute, Hour, Daily = "Tick", "Second", "Minute", "Hour", "Daily"
    ALL = (Tick, Second, Minute, Hour, Daily)


def resolution_to_timespan(resolution: str) -> int:
    """Common/Extensions.cs 2255-2273 ToTimeSpan(this Resolution): Tick -> TimeSpan.Zero,
    Second / Minute / Hour / Daily -> Time.OneSecond / OneMinute / OneHour / OneDay; anything
    else throws ArgumentOutOfRangeException. (100-ns ticks, like every DateTime here.)"""
    spans = {Resolution.Tick: 0, Resolution.Second: TICKS_PER_SECOND, Resolution.Minute: 60 * TICKS_PER_SECOND,
             Resolution.Hour: 3600 * TICKS_PER_SECOND, Resolution.Daily: 86_400 * TICKS_PER_SECOND}
    if resolution not in spans:
        raise ValueError(f"ArgumentOutOfRangeException: resolution {resolution!r}")
    return spans[resolution]


class QuoteBar(BaseData):
    """Common/Data/Market/QuoteBar.cs: the Quote data type of a bar resolution
    (LeanData.GetDataType, 492). Only its existence as a subscription's type is
    rewritten: the scenes carry no quotes, so no QuoteBar is ever made."""


def get_data_type(resolution: str, tick_type: str) -> type:
    """Common/Util/LeanData.cs 488-494 GetDataType(resolution, tickType):
    `if (resolution == Resolution.Tick) return typeof(Tick);
     if (tickType == TickType.OpenInterest) return typeof(OpenInterest);
     if (tickType == TickType.Quote) return typeof(QuoteBar);
     return typeof(TradeBar);` (OpenInterest: no CryptoFuture tick type is
    OpenInterest, SubscriptionManager.cs 361, so that branch cannot be reached here)."""
    if resolution == Resolution.Tick:
        return Tick
    if tick_type == "OpenInterest":
        raise NotImplementedError("OpenInterest is not a CryptoFuture tick type (SubscriptionManager.cs 361)")
    if tick_type == TickType.Quote:
        return QuoteBar
    return TradeBar


def is_valid_configuration(security_type: str, resolution: str, tick_type: str) -> bool:
    """Common/Util/LeanData.cs 520-527 IsValidConfiguration: false only for an
    Equity's Quote at Daily / Hour; true otherwise."""
    if security_type == "Equity" and resolution in (Resolution.Daily, Resolution.Hour):
        return tick_type != TickType.Quote
    return True


# Engine/DataFeeds/SubscriptionManager.cs 361 (the default data types):
# `{SecurityType.CryptoFuture, new List<TickType> {TickType.Trade, TickType.Quote}}`
AVAILABLE_DATA_TYPES = {SecurityType.CryptoFuture: [TickType.Trade, TickType.Quote]}


def lookup_subscription_config_data_types(security_type: str, resolution: str, is_canonical: bool) -> list[tuple[type, str]]:
    """Engine/DataFeeds/DataManager.cs 747-773 LookupSubscriptionConfigDataTypes:
    `if (isCanonical) { ... }` (753-761, a canonical option / future symbol: a
    CryptoFuture ticker added by AddCryptoFuture is not canonical -- the branch
    is kept and refuses); `AvailableDataTypes[symbolSecurityType].Where(tickType =>
    LeanData.IsValidConfiguration(...))` (763-765); `.Select(tickType => new
    Tuple<Type, TickType>(LeanData.GetDataType(resolution, tickType), tickType))`
    (767-768); `if (symbolSecurityType == SecurityType.CryptoFuture)
    result.Add(new Tuple<Type, TickType>(typeof(MarginInterestRate), TickType.Quote));` (770-773)."""
    if is_canonical:
        raise NotImplementedError("a canonical symbol's universe types (DataManager.cs 753-761) are not rewritten")
    available = [tt for tt in AVAILABLE_DATA_TYPES[security_type] if is_valid_configuration(security_type, resolution, tt)]
    result = [(get_data_type(resolution, tt), tt) for tt in available]
    if security_type == SecurityType.CryptoFuture:
        result.append((MarginInterestRate, TickType.Quote))
    return result


# Common/Global.cs 512-528 `public enum TickType { Trade, Quote, OpenInterest }`: the
# enum's numeric order is what SubscriptionCollection.SortSubscriptions orders by.
TICK_TYPE_RANK = {TickType.Trade: 0, TickType.Quote: 1, "OpenInterest": 2}


class SubscriptionDataConfig:
    """Common/Data/SubscriptionDataConfig.cs: the constructor 199-243 --
    `Type = objectType; Resolution = resolution; Symbol = symbol; ...
    IsInternalFeed = isInternalFeed; IsCustomData = isCustom; ...
    TickType = tickType ?? ...; Increment = resolution.ToTimeSpan();
    FillDataForward = resolution == Resolution.Tick ? false : fillForward;`
    (240-242) -- and equality 314-331 (the symbol, Type, TickType,
    Resolution, FillDataForward, ExtendedMarketHours, IsInternalFeed,
    IsCustomData, the time zones, the mapping mode, the depth offset,
    IsFilteredSubscription, the mapped flag). The time zones and the mapping
    fields are one value for every config made here (UTC; the defaults), so
    the equality below compares the other members.

    The feed adds a FillForwardEnumerator only when FillDataForward is true
    and the resolution is not Tick (FileSystemDataFeed.cs 239, 274-277); that
    enumerator is not rewritten, so the scene set runs with the public
    argument `fillForward: false` (QCAlgorithm.cs 2621 AddCryptoFuture), for
    which it is never added (`run` refuses a config with FillDataForward)."""

    def __init__(self, type_: type, symbol: str, resolution: str, fill_forward: bool, extended_hours: bool,
                 is_internal_feed: bool, is_custom: bool = False, tick_type: str | None = None,
                 security_type: str = "CryptoFuture", is_filtered_subscription: bool = True) -> None:
        self.Type, self.Resolution, self.Symbol, self.SecurityType = type_, resolution, symbol, security_type
        self.ExtendedMarketHours = extended_hours  # `&& LeanData.SupportsExtendedMarketHours(Type)`: false here
        self.IsInternalFeed, self.IsCustomData = is_internal_feed, is_custom
        self.IsFilteredSubscription = is_filtered_subscription
        if tick_type is None:  # `tickType ?? LeanData.GetCommonTickTypeForCommonDataTypes(...)`: every caller passes one
            raise NotImplementedError("GetCommonTickTypeForCommonDataTypes is not rewritten")
        self.TickType = tick_type
        self.Increment = resolution_to_timespan(resolution)
        self.FillDataForward = False if resolution == Resolution.Tick else fill_forward

    def _key(self) -> tuple:
        return (self.Symbol, self.Type, self.TickType, self.Resolution, self.FillDataForward, self.ExtendedMarketHours,
                self.IsInternalFeed, self.IsCustomData, self.IsFilteredSubscription)

    def __eq__(self, other) -> bool:
        return isinstance(other, SubscriptionDataConfig) and self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())


def supported_resolutions(type_: type, security_type: str) -> tuple:
    """Common/Data/BaseData.cs 252-260 SupportedResolutions: OptionResolutions for
    an option, else AllResolutions (47-48: every member of Resolution). Tick,
    TradeBar, QuoteBar and MarginInterestRate do not override it."""
    return Resolution.ALL


class DataManager:
    """Engine/DataFeeds/DataManager.cs: the algorithm's SubscriptionDataConfigService."""

    def __init__(self, live_mode: bool = False) -> None:
        self._subscription_manager_subscriptions: dict = {}
        self._live_mode = live_mode

    def Add(self, symbol: str, security_type: str, resolution: str | None = None, fill_forward: bool = True,
            extended_market_hours: bool = False, is_filtered_subscription: bool = True, is_internal_feed: bool = False,
            is_custom_data: bool = False, subscription_data_types: list | None = None) -> list:
        """DataManager.cs 602-738 Add(...). Rewritten:
          * 616-627 `var dataTypes = subscriptionDataTypes; if (dataTypes == null) { ... dataTypes =
            LookupSubscriptionConfigDataTypes(symbol.SecurityType, resolution ?? UniverseSettings.Resolution,
            symbol.IsCanonical()); }` (the custom-data branch 619-623 needs SecurityType.Base, not a CryptoFuture);
          * 629-632 no data types -> ArgumentNullException;
          * 634-687, the `resolutionWasProvided` side: in a backtest (`!_liveMode`) every type must
            support the resolution (676-685);
          * 704-727 one config per (type, tick type), internal when
            `subscriptionDataTypes == null && tickType == TickType.OpenInterest || isInternalFeed` (720-721);
          * 729-736 each config through SubscriptionManagerGetOrAdd (503-525).
        Not rewritten, and why they cannot hold for the scenes: 638-666 the `!resolutionWasProvided`
        side (the scene set always passes a resolution: refused here); 688-702 the market-hours entry,
        its time zones and their null checks (every config here is UTC; a CryptoFuture entry has both
        zones); 693-697 the Raw normalization of options and indexes (not a CryptoFuture)."""
        data_types = subscription_data_types
        if data_types is None:
            if resolution is None:
                raise NotImplementedError("resolution ?? UniverseSettings.Resolution: the scene set always passes one")
            data_types = lookup_subscription_config_data_types(security_type, resolution, is_canonical=False)
        if not data_types:
            raise ValueError("ArgumentNullException: At least one type needed to create new subscriptions")
        if resolution is None:
            raise NotImplementedError("the !resolutionWasProvided side (638-666) is not rewritten")
        for type_, _ in data_types:
            if not self._live_mode and resolution not in supported_resolutions(type_, security_type):
                raise ValueError(f"ArgumentException: Sorry {resolution} is not a supported resolution for {type_.__name__}")
        result = [SubscriptionDataConfig(type_, symbol, resolution, fill_forward, extended_market_hours,
                                         (subscription_data_types is None and tt == "OpenInterest") or is_internal_feed,
                                         is_custom_data, tick_type=tt, security_type=security_type,
                                         is_filtered_subscription=is_filtered_subscription)
                  for type_, tt in data_types]
        return [self.SubscriptionManagerGetOrAdd(c) for c in result]

    def SubscriptionManagerGetOrAdd(self, new_config):
        """DataManager.cs 503-525: `if (!_subscriptionManagerSubscriptions.TryGetValue(newConfig, out config))
        { _subscriptionManagerSubscriptions[newConfig] = config = newConfig; }` then return config."""
        if new_config not in self._subscription_manager_subscriptions:
            self._subscription_manager_subscriptions[new_config] = new_config
        return self._subscription_manager_subscriptions[new_config]


class UserDefinedUniverse:
    """Common/Data/UniverseSelection/UserDefinedUniverse.cs. `Add(SubscriptionDataConfig)`
    (140-155) puts the config into the HashSet `_subscriptionDataConfigs` (an
    equal config is not added twice). `GetSubscriptionRequests` (225-261)
    returns one request per config of that set whose symbol is the security's
    (233); its branches 234-247 (`_pendingRemovedConfigs`, the base class's
    requests) run only when the set has no config of the symbol, which
    cannot happen after an AddCryptoFuture put its configs in (refused here).
    A HashSet's order is not fixed by the source; the order kept here is the
    order the configs were added, and the order the synchroniser visits the
    subscriptions in is fixed by its own sort (`sort_subscriptions`) up to
    ties, which the reproduction runs both ways."""

    def __init__(self) -> None:
        self._subscription_data_configs: dict = {}
        self.Members: dict = {}

    def Add(self, config) -> bool:
        if config in self._subscription_data_configs:
            return False
        self._subscription_data_configs[config] = None
        return True

    def GetSubscriptionRequests(self, symbol: str) -> list:
        result = [c for c in self._subscription_data_configs if c.Symbol == symbol]
        if not result:
            raise NotImplementedError("the _pendingRemovedConfigs / base-class branches (234-247) are not rewritten")
        return result

    def Selected(self) -> list:
        out: list = []
        for c in self._subscription_data_configs:
            if c.Symbol not in out:
                out.append(c.Symbol)
        return out


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
    """Algorithm/QCAlgorithm.cs: the user's algorithm overrides Initialize and
    OnData(Slice) (Common/Interfaces/IAlgorithm.cs 521); `Time` is the
    algorithm's clock, set by SetDateTime. Round r8-1: the user adds its
    security through the public `AddCryptoFuture`."""

    NULL_LEVERAGE = 0.0  # Securities/Security.cs Security.NullLeverage (the argument's default)

    def __init__(self) -> None:
        self.UtcTime = 0
        self.DataManager = DataManager()  # SubscriptionManager.SubscriptionDataConfigService
        self._user_defined_universe = UserDefinedUniverse()
        self._pending_user_defined_universe_security_changes: list = []
        self.Securities: dict = {}

    def Initialize(self) -> None:  # noqa: N802 - LEAN's name
        pass

    def SetDateTime(self, utc: int) -> None:
        self.UtcTime = utc

    def OnData(self, slice_: Slice) -> None:  # noqa: N802 - LEAN's name
        pass

    def AddCryptoFuture(self, ticker: str, resolution: str | None = None, market: str | None = None,
                        fill_forward: bool = True, leverage: float = NULL_LEVERAGE):
        """QCAlgorithm.cs 2621-2624: `return AddSecurity<CryptoFuture>(SecurityType.CryptoFuture,
        ticker, resolution, market, fillForward, leverage, false);` (extendedMarketHours = false)."""
        return self._add_security("CryptoFuture", ticker, resolution, market, fill_forward, leverage, False)

    def _add_security(self, security_type: str, ticker: str, resolution, market, fill_forward, leverage,
                      extended_market_hours: bool):
        """QCAlgorithm.cs 3069-3087 AddSecurity<T>: `market = GetMarket(...)`; the symbol from the
        ticker (3076-3081); `var configs = SubscriptionManager.SubscriptionDataConfigService.Add(symbol,
        resolution, fillForward, extendedMarketHours, dataNormalizationMode: ..., dataMappingMode: ...)`
        (3083-3085); `var security = Securities.CreateSecurity(symbol, configs, leverage)`;
        `return (T)AddToUserDefinedUniverse(security, configs)`. Not rewritten: GetMarket and
        Symbol.Create (the scene set's symbol is one ticker string; market and leverage are left at
        their defaults and nothing rewritten here reads them), CreateSecurity's security model (it
        holds the configs it is given; the data path reads the configs only)."""
        symbol = ticker
        configs = self.DataManager.Add(symbol, security_type, resolution, fill_forward, extended_market_hours)
        security = {"Symbol": symbol, "Subscriptions": list(configs), "Leverage": leverage, "Market": market}
        return self._add_to_user_defined_universe(security, configs)

    def _add_to_user_defined_universe(self, security: dict, configurations: list):
        """QCAlgorithm.Universe.cs 580-650 AddToUserDefinedUniverse: the security goes into
        Securities unless it is there already (586-600; replaced only when the existing one is an
        internal feed and the new config is not, 588-595: a user's CryptoFuture is never internal);
        the user-defined universe of the security type and market is created once (603-633); then
        `_pendingUserDefinedUniverseSecurityChanges.Add(new UserDefinedUniverseUpdate(universe,
        configurations, security))` (640)."""
        if security["Symbol"] not in self.Securities:
            self.Securities[security["Symbol"]] = security
        self._pending_user_defined_universe_security_changes.append((self._user_defined_universe, configurations, security))
        return self.Securities[security["Symbol"]]

    def OnEndOfTimeStep(self) -> None:
        """QCAlgorithm.Universe.cs 70-179: with pending user-defined changes (75), for each addition
        `foreach (var subscriptionDataConfig in ...SubscriptionDataConfigs) changedCollection |=
        ...Universe.Add(subscriptionDataConfig);` (149-158), then the pending list is cleared (178).
        Not rewritten, and why they cannot hold: 83-133 the derivative / underlying handling (a
        CryptoFuture has no underlying), 135-138 seeding (live mode only), removals (161-165: none)."""
        for universe, configurations, _security in self._pending_user_defined_universe_security_changes:
            for config in configurations:
                universe.Add(config)
        self._pending_user_defined_universe_security_changes.clear()

    def _universe_selection(self) -> list:
        """Engine/DataFeeds/UniverseSelection.cs 252-298 (ApplyUniverseSelection): for each selected
        symbol that is not already a member (254-258), `foreach (var request in
        universe.GetSubscriptionRequests(security, ...))` (272) ... `_dataManager.AddSubscription(request)`
        (298): one data feed subscription per config. Not rewritten, and why they cannot hold: 274-279
        a request without tradable days (a CryptoFuture trades every day), 289-294 the internal
        currency feed removal (no currency conversion subscription is added here), 260-264 the
        underlying (none). Returns the configs in the order the subscriptions were added."""
        added = []
        for symbol in self._user_defined_universe.Selected():
            if symbol in self._user_defined_universe.Members:
                continue
            requests = self._user_defined_universe.GetSubscriptionRequests(symbol)
            self._user_defined_universe.Members[symbol] = requests
            added.extend(requests)
        return added


def run(algorithm: QCAlgorithm, reader, reverse_ties: bool = False) -> None:
    """The engine's run of one algorithm (round r8-1: from the user's Initialize).

    Engine/Setup/BacktestingSetupHandler.cs calls `algorithm.Initialize()`; the
    pending security additions are processed at the end of that step
    (`OnEndOfTimeStep`, above) and the universe selection makes one
    subscription per config (above). `reader(config)` is the data of that
    config's source -- the file the user placed for it (the scene set's side:
    the scene's events written as that config's data). Then, as
    Engine/AlgorithmManager.cs Run: for each time slice of the feed (191),
    `algorithm.SetDateTime(time)` (244), then `if (timeSlice.Slice.HasData)
    algorithm.OnData(algorithm.CurrentSlice)` (582-586).
    Conditions not rewritten, and why they cannot hold for the scenes: 197-201
    and 360-369 the algorithm's status is not Running / a runtime error (the
    scenes' algorithm only records); 204 cancellation (none); 216 the
    portfolio value <= 0 in a backtest (the scenes place no order; LEAN's
    default cash is not zero); 247 a time pulse (emitted only around universe
    selection, SubscriptionSynchronizer.cs 225-229). A security added while the
    algorithm runs (an AddCryptoFuture inside OnData) is applied at the end of
    that time step and selected at a later frontier: that path is not
    rewritten and is refused. `reverse_ties` hands the subscriptions to the
    collection in the reverse order (ties of its sort are not fixed by the source)."""
    algorithm.Initialize()
    algorithm.OnEndOfTimeStep()
    configs = algorithm._universe_selection()
    for c in configs:
        if c.FillDataForward:
            raise NotImplementedError("FillForwardEnumerator (FileSystemDataFeed.cs 239, 274-277) is not rewritten")
    subs = [Subscription(reader(c), c, utc_start_time=0) for c in configs]
    if reverse_ties:
        subs = list(reversed(subs))
    adding = algorithm.AddCryptoFuture

    def refuse(*a, **k):
        raise NotImplementedError("adding a security while the algorithm runs is not rewritten")
    algorithm.AddCryptoFuture = refuse
    try:
        for ts in sync(subs, 0):
            algorithm.SetDateTime(ts.UtcTime)
            if ts.HasData:
                algorithm.OnData(ts)
    finally:
        algorithm.AddCryptoFuture = adding
