# coding: utf-8
import ccxt
from bitmex import bitmex
import json
import time
from datetime import datetime, timedelta
import configparser
import requests

# --------------------------------------------------
# ローソク足とヒゲでトレードするMEXbot
# 実足の向きと長さをヒゲの長さと比べる
# 長さはとりあえず15分足で
# --------------------------------------------------
# 設定ファイル読み込み

inifile = configparser.ConfigParser()
inifile.read('./config.ini', 'UTF-8')
apikey = inifile.get('MEX_APIKEY898', 'apikey')
secret = inifile.get('MEX_APIKEY898', 'secret')

ccbm = ccxt.bitmex({
    'apiKey': apikey,
    'secret': secret,
})
api = bitmex(test=False, api_key=apikey, api_secret=secret)

WHURL_t = 'REDACTED_WEBHOOK_URL'
WHURL_r = 'REDACTED_WEBHOOK_URL'


# --------------------------------------------------
# 設定値
sizedef = 3000
sizemax = sizedef * 2
foot = 15 # 時間足
candlelen = 0 # ローソク足判定長さ
beardline = 19 # ヒゲ判定長さ
bigbeardline = 24 #大ヒゲ判定長さ

# 変数定義
price_open = 0
price_high = 0
price_Low = 0
price_close = 0
mybtc = 0
entry_price = 0
size = 0
signal = 0
candle = 0
length = 0
topbeard = 0
underbeard = 0
candleSign = 0
lcprice = 0
candleList = []
candleSignList = []
signalList = []
topbeardList = []
underbeardList = []

Time, Open, High, Low, Close = [], [], [], [], []




# --------------------------------------------------

# パラメータと言いたいこと(say)をつぶやくメソッド
def pripara(say):
    global entry_price, lcprice
    msg = ('{} ${} ローソク:{} 上ヒゲ:{} 下ヒゲ:{} 「{}」 ポジ: {}枚 ${} ヒゲライン{}'.format(
            str(Time[-1]),
            str(Close[-1]),
            str(candle),
            str(topbeard),
            str(underbeard),
            str(say),
            str(mybtc),
            str(entry_price),
            str(lcprice)
            ))
    print(msg)
    info_discord(msg, WHURL_r)
    return

# discord通知
def info_discord(message, url):
    while True:
        for x in range(2):
            try:
                discord_webhook_url = url
                data = {"content": " " + message + " "}
                requests.post(discord_webhook_url, data=data)
                break
            except Exception as e:
                if x == 0 or x == 1:
                    msg = 'discord通信エラー'
                    print(msg)
                    time.sleep(5)
                else:
                    msg = 'discordが不安定、スルーします'
                    print(msg)
        break

# 時間計測とポジション情報取得
def fetch_current(x):
    while True:
        if datetime.now().minute % 15 == 0 and datetime.now().second == x:
            global error
            error = 0
            break
        time.sleep(0.5)

def fetch_mex():
    while True:
        try:
            global position
            position = ccbm.private_get_position({'filter': json.dumps({"symbol": "XBTUSD"})})
            try:
                global mybtc
                mybtc = position[0]['currentQty']
                global entry_price
                entry_price = position[0]['avgEntryPrice']
            except Exception as e:
                mybtc = 0
                entry_price = 0
            break
        except Exception as e:
            print('[ERROR: BitMEXからの情報取得に問題が発生しました。15秒後に再取得します。]')
            time.sleep(15)

# ローソク足の取得と判定

def get_candle_first(foot):
    global signal, candle, length, topbeard, underbeard, candleSign, lcprice, totallen, candlelen
    unixTime = lambda y, m, d, h, minu: int(time.mktime(datetime(y, m, d, h, minu).timetuple()))
    now = datetime.today()
    after = now - timedelta(minutes=foot*2)
    y, m, d, h, minu = now.year, now.month, now.day, now.hour, now.minute
    ay, am, ad, ah, aminu = after.year, after.month, after.day, after.hour, after.minute
    periods = 60 * int(foot)
    url = 'https://api.cryptowat.ch/markets/bitmex/btcusd-perpetual-futures/ohlc'
    query = {
        'periods': periods,  # 60→1分足　3600→1時間足　日足→86400
        'before': unixTime(y, m, d, h, minu),
        'after': unixTime(ay, am, ad, ah, aminu),
    }
    data = requests.get(url, params=query).json()['result']['900']
    for i in data:
        Time.append(datetime.fromtimestamp(data[-1][0]))
        Open.append(data[-1][1])
        High.append(data[-1][2])
        Low.append(data[-1][3])
        Close.append(data[-1][4])
        candle = Close[-1] - Open[-1]
        totallen = High[-1] - Low[-1]
        candleList.append(candle)
        if candle > 0:
            candleSign = 1
        elif candle < 0:
            candleSign = -1
        else:
            candleSign = 0
        candleSignList.append(candleSign)
        if candleSign == 1:
            topbeard = High[-1] - Close[-1]
            underbeard = Open[-1] - Low[-1]
            if topbeard > abs(candle) and int(topbeard) > int(underbeard):
                signal = -1
                lcprice = High[-1]
            elif underbeard > abs(candle) and int(underbeard) > int(topbeard):
                signal = 1
                lcprice = Low[-1]
            else:
                signal = 0
        elif candleSign == -1:
            topbeard = High[-1] - Open[-1]
            underbeard = Close[-1] - Low[-1]
            if underbeard > abs(candle) and int(underbeard) > int(topbeard):
                signal = 1
                lcprice = Low[-1]
            elif topbeard > abs(candle) and int(topbeard) > int(underbeard):
                signal = -1
                lcprice = High[-1]
            else:
                signal = 0
        else:
            topbeard = High[-1] - Open[-1]
            underbeard = Close[-1] - Low[-1]
            signal = 0
        topbeardList.append(topbeard)
        underbeardList.append(underbeard)
        signalList.append(signal)

    
def get_candle(foot):
    global signal, candle, length, topbeard, underbeard, candleSign, lcprice, totallen, candlelen
    unixTime = lambda y, m, d, h, minu: int(time.mktime(datetime(y, m, d, h, minu).timetuple()))
    now = datetime.today()
    after = now - timedelta(minutes=foot)
    y, m, d, h, minu = now.year, now.month, now.day, now.hour, now.minute
    ay, am, ad, ah, aminu = after.year, after.month, after.day, after.hour, after.minute
    periods = 60 * int(foot)
    url = 'https://api.cryptowat.ch/markets/bitmex/btcusd-perpetual-futures/ohlc'
    query = {
        'periods': periods,  # 60→1分足　3600→1時間足　日足→86400
        'before': unixTime(y, m, d, h, minu),
        'after': unixTime(ay, am, ad, ah, aminu),
    }
    response = requests.get(url, params=query)
    for x in range(2):
        try:
            response.raise_for_status()
            data = response.json()['result'][str(periods)]
        except Exception as e:
            if x == 0 or x == 1:
                msg = 'error by cryptowatch, retry'
                print(msg)
                time.sleep(5)
            else:
                msg = 'error by cryptowatch'
                print(msg)
        else:
            Time.append(datetime.fromtimestamp(data[-1][0]))
            Open.append(data[-1][1])
            High.append(data[-1][2])
            Low.append(data[-1][3])
            Close.append(data[-1][4])
            candle = Close[-1] - Open[-1]
            totallen = High[-1] - Low[-1]
            candleList.append(candle)
            if candle > 0:
                candleSign = 1
            elif candle < 0:
                candleSign = -1
            else:
                candleSign = 0
            candleSignList.append(candleSign)
            if candleSign == 1:
                topbeard = High[-1] - Close[-1]
                underbeard = Open[-1] - Low[-1]
                if topbeard > abs(candle) and int(topbeard) > int(underbeard):
                    signal = -1
                    lcprice = High[-1]
                elif underbeard > abs(candle) and int(underbeard) > int(topbeard):
                    signal = 1
                    lcprice = Low[-1]
                else:
                    signal = 0
            elif candleSign == -1:
                topbeard = High[-1] - Open[-1]
                underbeard = Close[-1] - Low[-1]
                if underbeard > abs(candle) and int(underbeard) > int(topbeard):
                    signal = 1
                    lcprice = Low[-1]
                elif topbeard > abs(candle) and int(topbeard) > int(underbeard):
                    signal = -1
                    lcprice = High[-1]
                else:
                    signal = 0
            else:
                topbeard = High[-1] - Open[-1]
                underbeard = Close[-1] - Low[-1]
                signal = 0
            topbeardList.append(topbeard)
            underbeardList.append(underbeard)
            signalList.append(signal)



# 注文処理
def orderset(size1, price1, size2, price2, buy=True):
    if buy:
        size1 = size1
        size2 = size2
    else:
        size1 = -size1
        size2 = -size2

    common_params = {
        'symbol': 'XBTUSD',
        'orderQty': size,
    }
    orders = [
        dict(common_params,
             orderQty=size1,
             price=price1,
             execInst='ParticipateDoNotInitiate',
             ),
        dict(common_params,
             orderQty=size2,
             price=price2,
             )
    ]
    return orders


def order_buy():
    print('----------------------------------------------------------------------------------')
    for x in range(2):
        try:
            if abs(mybtc) >= sizemax:
                api.Order.Order_cancelAll().result()
                book = ccbm.fetch_order_book('BTC/USD')
                price1 = book["bids"][0][0]
                size = sizedef
                prize2 = price1 - abs((price1 - lcprice) / 2)
                if mybtc == 0:
                    msg = 'ヒゲは裏切らねぇ！' + str(price1) + 'で買いだ！'
                    orders = orderset(size, price1, size, prize2, buy=True)
                elif mybtc < 0:
                    msg = 'ヒゲは裏切らねぇ！ドテンで' + str(price1) + 'で買いだ！ ポジ:' + str(mybtc) + '枚 ' + str(entry_price)
                    orders = orderset(size + mybtc, price1, size, prize2, buy=True)
                else:
                    msg = 'ヒゲは裏切らねぇ！' + str(price1) + 'で買い増しだ！ ポジ:' + str(mybtc) + '枚 ' + str(entry_price)
                    orders = orderset(size, price1, size, prize2, buy=True)
                api.Order.Order_newBulk(orders=json.dumps(orders)).result()
            else:
                msg = 'ポジションオーバー！注文はスルーするぜ'
            print(msg)
            info_discord(msg, WHURL_t)
            break
        except Exception as e:
            if x == 0 or x == 1:
                msg = '注文を送信できず。1秒後に1度リトライ！'
                print(msg)
                info_discord(msg, WHURL_t)
                time.sleep(1)
            else:
                msg = '通らねぇか...！'
                print(msg)
                info_discord(msg, WHURL_t)
    print('----------------------------------------------------------------------------------')

def order_sell():
    print('----------------------------------------------------------------------------------')
    for x in range(2):
        try:
            if abs(mybtc) >= sizemax:
                api.Order.Order_cancelAll().result()
                book = ccbm.fetch_order_book('BTC/USD')
                price1 = book["asks"][0][0]
                size = sizedef
                prize2 = price1 + abs((price1 - lcprice) / 2)
                if mybtc == 0:
                    msg = 'ヒゲは裏切らねぇ！' + str(price1) + 'で売りだ！'
                    orders = orderset(size, price1, size, prize2, buy=False)
                elif mybtc > 0:
                    msg = 'ヒゲは裏切らねぇ！ドテンで' + str(price1) + 'で売りだ！  ポジ:' + str(mybtc) + '枚 ' + str(entry_price)
                    orders = orderset(size + mybtc, price1, size, prize2, buy=False)
                else:
                    msg = 'ヒゲは裏切らねぇ！' + str(price1) + 'で売り増しだ！ ポジ:' + str(mybtc) + '枚 ' + str(entry_price)
                    orders = orderset(size, price1, size, prize2, buy=False)
                api.Order.Order_newBulk(orders=json.dumps(orders)).result()
            else:
                msg = 'ポジションオーバー！注文はスルーするぜ'
            print(msg)
            info_discord(msg, WHURL_t)
            break
        except Exception as e:
            if x == 0 or x == 1:
                msg = '注文を送信できず。1秒後に1度リトライ！'
                print(msg)
                info_discord(msg, WHURL_t)
                time.sleep(1)
            else:
                msg = '通らねぇか...！'
                print(msg)
                info_discord(msg, WHURL_t)
    print('----------------------------------------------------------------------------------')

def orderset_exit(price, size, buy=True):
    if buy:
        size = size
        sign = 1
    else:
        size = -int(size)
        sign = -1

    common_params = {
        'symbol': 'XBTUSD',
        'orderQty': size,

    }
    orders = [
        dict(common_params,
             price=price,
             execInst='ReduceOnly, ParticipateDoNotInitiate',
             ),
        dict(common_params,
             ordType='StopLimit',
             execInst='ReduceOnly, ParticipateDoNotInitiate, LastPrice',
             stopPx=price + (sign * 1.5),
             price=price + (sign * 1),
             ),
        dict(common_params,
             ordType='StopLimit',
             execInst='ReduceOnly, ParticipateDoNotInitiate, LastPrice',
             stopPx=price + (sign * 3.5),
             price=price + (sign * 3),
             ),
        dict(common_params,
             ordType='Stop',
             execInst='ReduceOnly',
             stopPx=price + (sign * 5)
             )
    ]
    return orders

def order_exit():
    print('----------------------------------------------------------------------------------')
    for x in range(2):
        try:
            api.Order.Order_cancelAll().result()
            book = ccbm.fetch_order_book('BTC/USD')
            if mybtc < 0:
                size = -mybtc
                price = book["bids"][0][0]
                orders = orderset_exit(price, size, buy=True)
            elif mybtc > 0:
                size = mybtc
                price = book["asks"][0][0]
                orders = orderset_exit(price, size, buy=False)
            api.Order.Order_newBulk(orders=json.dumps(orders)).result()
            msg = str(price) + 'でトンズラするぜ！  ポジ:' + str(mybtc) + '枚 ' + str(entry_price)
            print(msg)
            info_discord(msg, WHURL_t)
            break
        except Exception as e:
            if x == 0:
                msg = '注文を送信できず。1秒後に1度リトライ！'
                print(msg)
                info_discord(msg, WHURL_t)
                time.sleep(1)
            else:
                msg = '通らねぇか...！'
                print(msg)
                info_discord(msg, WHURL_t)
    print('----------------------------------------------------------------------------------')

def order_out():
    print('----------------------------------------------------------------------------------')
    for x in range(2):
        try:
            api.Order.Order_cancelAll().result()
            if mybtc < 0:
                size = -mybtc
                ccbm.create_order('BTC/USD', type='market', side='buy', amount=size)
            elif mybtc > 0:
                size = mybtc
                ccbm.create_order('BTC/USD', type='market', side='sell', amount=size)
            msg = 'ミスったぜ...撤退だ...  ポジ:' + str(mybtc) + '枚 ' + str(entry_price)
            print(msg)
            info_discord(msg, WHURL_t)
            break
        except Exception as e:
            if x == 0:
                msg = '注文を送信できず。1秒後に1度リトライ！'
                print(msg)
                info_discord(msg, WHURL_t)
                time.sleep(1)
            else:
                msg = '通らねぇか...！'
                print(msg)
                info_discord(msg, WHURL_t)
    print('----------------------------------------------------------------------------------')


# --------------------------------------------------
# 起動メッセージと設定値入力

print('--------------------------------------------------------------')
print('                 カツオ・ザ・ヒゲトレーダー③！              ')
print('--------------------------------------------------------------')
print('ヒゲトレード開始だ！ポジションサイズ:' + str(sizedef))

# --------------------------------------------------
# 初回起動
fetch_mex()
get_candle_first(foot)
pripara('準備万端だ！')

# 以下毎15分ループ
while True:

    fetch_current(1)
    fetch_mex()
    get_candle(foot)
    if candleSign == 1:  # 陽線
        if signal == -1:  # 上ヒゲ
            if mybtc > 0:
                pripara('上ヒゲ陽線！引き上げるぜ')
                order_exit()
            else:
                pripara('上ヒゲ陽線！売るぜ')
                order_sell()
        elif signal == 1:  # 下ヒゲ
            pripara('下ヒゲ陽線！買うぜ！')
            order_buy()
        else:
            if mybtc > 0:
                pripara('上がれ...！')
            elif mybtc == 0:
                pripara('陽線...見守るぜ')
            elif mybtc < 0:
                if Close[-1] < lcprice:  # ヒゲライン超えず
                    pripara('陽線...まだこらえるんだ...！')
                else:
                    pripara('陽線...引き上げるぜ')
                    order_exit()
    elif candleSign == -1:  # 陰線
        if signal == 1:  # 下ヒゲ
            if mybtc < 0:
                pripara('下ヒゲ陰線！引き上げるぜ')
                order_exit()
            else:
                pripara('下ヒゲ陰線！買うぜ')
                order_buy()
        elif signal == -1:  # 上ヒゲ
            pripara('上ヒゲ陰線！売るぜ')
            order_sell()
        else:
            if mybtc < 0:
                pripara('下がれ...！')
            elif mybtc == 0:
                pripara('陰線...見守るぜ')
            elif mybtc > 0:
                if Close[-1] > lcprice:  # ヒゲライン超えず
                    pripara('陰線...まだこらえるんだ...！')
                else:
                    pripara('陰線...引き上げるぜ')
                    order_exit()
    else:
        pripara('見守るぜ')
    time.sleep(1)
