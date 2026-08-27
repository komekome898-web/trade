# coding: utf-8
import websocket
import json
import threading
from datetime import datetime, timedelta
import configparser
import requests
import pybitflyer
import time
import sys
from multiprocessing import Process

# ↑のimportで足りてないものは各自pipコマンドでインストールしておいてね。
# 多分 pybitflyerとwebsocketが要インストールだと思う。下のpipコマンドを実行してね。
# pip install pybitflyer
# pip install websocket-client==0.52.0

# このBotの概要----------------------------------------------------------------------------------
# レンジでナンピンする子 「マチルダ」ちゃん
# レンジの上方でS、下方でL、中央付近で決済するよ。
# レンジである限り損はしない。損する時はレンジブレイク時と利確指値に届かない長期間のポジ保有時
# あくまで裁量してない時 or ポジとりにくいクソレンジ相場で使ってね。
# ※レンジブレイク時の挙動
#   ポジションを成行で解消、注文の取り消し及びブレイク方向へ指値エントリー
#   こういう時はbfめっちゃ重くなって中々注文が通らなくて思いのほか損する可能性があるよ。
#   その時はごめんなさい。みなさんの感覚で動かすタイミングを決めてもらえるといいかも。
# ------------------------------------------------------------------------------------------くみたそ＊

# version履歴-------------------------------------------------------------------------------------------------------------------
# 01 お披露目                                                                                                       2019/02/02
# 02 日付マタギとメンテマタギでポジらないようにしました                                                             2019/02/03
# 03 エントリー位置・利確位置・指値間隔を変えられる項目、およびブレイク時のロットの項目を追加                       2019/02/04
# 04 起動時のデータ収集のバグ修正、またそれに伴って設定値の追加                                                     2019/02/04
# 05 メンテ後の再稼働時間を4:15に変更 APIとWEBHOOKをconfigファイルに外出し
#    ブレイク時の追い成でsizebreak以上の注文を出すバグを修正                                                        2019/02/06
# 06 sizemin以下のポジの利確指値を出すように修正 discord通知flgが読み込めないバグを修正
#    volaの計算ができていないバグを修正（←私の運用ロジックで上書きしただけ）                                       2019/02/08
#
# 11 ロジック大幅変更に伴うバージョンアップ(0xシリーズ → 1xシリーズ)
#    利確指値用関数(order_exit)を実装
#    上記に伴い設定値sizebigを実装し、ポジションの利確を早める処理を導入
#    コンソール出力に時間を明記するよう修正
#    デフォルト値を秒スキャ対応値に変更                                                                             2019/02/16
# 12 暫定エラー対策として次の二つをハンドリング ①100000円以下の利確指値 ②証拠金オーバーの注文
#    長期ポジの強制決済を行わないバグと損切指値変更をしないバグを修正、コンソールにポジった時間表示
#    起動時に注文をキャンセルする処理を追加（再起動時に利確指値とかキャンセルするんめんどくさくて）                 2019/02/22
#
# 21 ロジック大幅変更に伴うバージョンアップ(1xシリーズ → 2xシリーズ)
#    discord通知内容を大幅に変更
#     ・毎分各計算値を定期通知（ログ・死活監視の役目を含む）またこれに伴いブレイク時のログ出力を廃止
#     ・各アラートはeveryone通知を使用（ブレイク時、ブレイクオフ時、長期ポジ保有時、大きいポジ保有時）
#    この前のサーキットブレイクにビビったので、ブレイクの判定と挙動の変更
#     ・ブレイク時のエントリーを成行→指値に変更。また利確値幅の設定値[break_exit_setting]を追加。
#     ・ブレイク判定を早くする（もしくはブレイク判定をなくす）設定値[break_delay]を追加。
#    ノーポジ時に指値をなるべく約定させようと努力するように変更
#    CryptoWatchからのデータ取得の際のエラーをハンドリング（めだまんさんスペシャルサンクス）                        2019/03/08
#
# 22 毎分データ計算の実装ミスがあったので修正
#    LineNotifyを実装（こころんスペシャルサンクス）
#    レンジの確度を示すフラグ[expantion_flg]を実装、今後戦略に利用していく所存
#    上記のフラグに応じて設定値を書き換える機能を実験的に＆簡易的に実装                                             2019/03/11
#
# 31 秒スキャ用に完全リニューアル(2xシリーズ → 3xシリーズ)
#    変更されたbfAPI/cwAPIの制限に対応
#    構造をWS/bfAPI/cwAPIに変更
#    利確に板を使う仕様に変更 利確値幅を決められる様に変更(step_exit)
#    複利ロット計算機能を追加                                                                                       2019/06/09
#
# 37 なんやかんやあって落ち着いて運用できる形になったもの
#    さらに変更されたbfAPI/cwAPIの制限に対応
#    sizeminを基準にポジ数によって利確値幅(vola*step_exit)を按分して、決済時の収益性を平滑化
#    break時の仕様を変化
#     ・倍のレンジの高値安値以内はブレイクにしない
#     ・ブレイク方向のポジでナンピン
#     ・出来高のある逆行を検知して利確指値を出す 二回連続の逆行でポジブン投げ、順行するまで一旦エントリー停止
#     ・breakexitsizeで指定したポジ数までは利確指値を出さない（たまに数万幅とかとれる）
#    ※懸念点
#    　bfAPIが返してくるエラーで意味わからんのがあって、そんときは止めて時間おいて起動しなおす手間がいる      2019/09/04
# ------------------------------------------------------------------------------------------------------------------------------

# 各自の設定値ココカラ--------------------------------------------------
# 設定ファイルから読み出し
# matilda.config.iniを開いて、*******の部分を各自のAPIやURLに書き換えてね。discord通知を使うならflgを1にしてね。
# 更新の度にAPIキーとか打ち直す手間が省けるよ。
inifile = configparser.ConfigParser()
inifile.read('./matilda_config.ini', 'UTF-8')
apikey = inifile.get('bF_APIKEY', 'apikey')
secret = inifile.get('bF_APIKEY', 'secret')

public_api = pybitflyer.API()
api = pybitflyer.API(api_key=apikey, api_secret=secret)

# レンジブレイク時、ポジション長期保有時にdiscordにアラートをする機能があります。1ならON、0ならOFFです。
# 使いたい場合はmatilda_config.iniのflg=1にして、matilda_alertにdiscordWebHookのURLを入れてね。
discord_flg = inifile.getint('DISCORD_WEBHOOK', 'flg')
WHURL_a = inifile.get('DISCORD_WEBHOOK', 'matilda_alert')

# LINE通知機能
LINE_NOTIFY_API_URL = 'https://notify-api.line.me/api/notify'
line_flg = inifile.getint('LINE_NOTIFY', 'flgforline')
LINE_NOTIFY_TOKEN = inifile.get('LINE_NOTIFY', 'line_token')

# --------------------------------------------------
# 設定値
# デフォルトは私の運用中の値。適宜自分用に変えていってほしいけど、ロット関係以外はBotの性能に直結するので一旦このままがいいかも。
# デフォルトは秒スキャ用の高ロット高頻度設定。ボラのあるレンジを狙って使ってたら日次8000円とれたよ。証拠金は6万円。
# ※高ロット運用は基本的に危険だよ!!!レンジである確度が高いと思った日にこの設定にしてね。
# 注文ロット関係。基本はナンピンBotなのでここの調整ミスると危険だよ。
sizemin = 0.02  # 最小ロット。このサイズの指値をいっぱいまくよ。
sizemax = 0.14  # 最大ロット。ポジションがここまで肥大すると注文をやめるよ。許容する証拠金に応じて決めてね。
sizealert = 0.15  # この数値以上のポジを持つとお知らせするよ。毎分するよ。んで損切りor撤退指値を出すよ。
sizealert_limit = 1  # この回数お知らせするよ。お知らせ自体いらないなら0にしてね。
breakexitsize = 3  # ブレイク時に利確指値を出し始めるポジ個数だよ。ほんまの大動きのときに大値幅とって損失の補填ができるよ。

fukuri = 1  # 1にするとロットを自動計算するよ。長期複利運用をする人用。いらんなら0にしてね。
leverage = 4  # レバだよ
collateral_using = 0.9  # 証拠金の何割使うかだよ。
pos_count = 7  # sizemin何個分のポジを最大もつかきめるよ（sizemax）
alert_ratio = 7  # sizemin何個分のポジでアラートするかきめるよ（sizealert）


# 基準時間足。ボラやレンジ幅の計算や、利確指値を出す間隔に影響するよ。一旦デフォルト値のままがオススメ。
foot = 1  # 基準時間足(分) 。1なら1分足更新のタイミングでもろもろ計算するよ。まだ他の時間足は試してない。
vola_count = 40  # (分)この時間分の平均ボラを計算するよ。
range_count = 40  # (分)この時間分のレンジ幅を計算するよ。
alert_count = 20  # (分)この時間分ポジションに変更がなかったらクソポジと判断してアラートがなるよ。
#                             ポジションがレンジ中央値より悪いと、損切指値を出すよ
#                             その後、更にこの時間分持ち続けてたら、損益に関わらず強制決済するよ。
#                             ポジションの回転数をあげたかったらもっと短くしてもいいよ。

# ボラとレンジ幅のしきい値設定。どちらかがこの数値以下の場合エントリーをしなくなるよ。ポジポジ病防止の役目をするよ。
# ポジションとる頻度と値幅に関わってくるから、うまく調整できると化けると思う。
#vola_setting = 1  # 毎分計算してるボラがこの数値以下になるとエントリーしなくなるよ。
range_setting = 150  # レンジ幅がこの数値以下になるとエントリーしなくなるよ。
over_range_setting = 100000  # レンジ幅がこの数値以上になるとエントリーしなくなるよ。

# 利確指値とエントリー指値の中央値からの距離を決める値。毎分計算するボラ（vola）にこれらの値を掛けて、指値価格を決めるよ。
# （中央値から entry_setting×vola だけ現在価格が離れるとエントリー開始。利確は中央値から exit_setting×vola 離れたところ）
# ※ ここをいじる際は必ず entry_setting > exit_setting となるようにしてね。この差分が利益になるからね。
# ※ デフォルトは 3:2 にしてるけど、慎重派は 4:3 、欲張りさんは 5:1 、高回転の 2:1 みたいに自由に決めてね。
entry_setting = 2  # 大きくするにつれ中央値から離れたところでエントリーするよ。
exit_setting = 0.8  # 大きくするにつれ中央値から離れたところで利確するよ。

break_delay = 1  # 連続で高値更新とかが起こると、ブレイク判定値も連続で上がってしまって、中々ブレイクしないのが
# 弱点だったけど、これを 3 にするとブレイク判定の更新を3分遅らせて、比較的緩やかなトレンドを察知しやすくなるよ。
# 要するに大きくすればブレイクしやすくなるよ。range_countを大きめに設定するときはこれも大きくすると良いきがする。
# ※ちなみに 0 にするとブレイク自体しなくなる！（はず、未検証）。
# sizemaxに余裕があるならブレイク損切りはいらないのでそういう人は 0 も試してみてね。
# 私はこわくてよーせん）

beard_ignore = 1  # この数値以上の長い髭を無視してレンジ計算するよ。
# bfは大口雑成行とmmbotterによるクソ髭ができやすいから、それによってレンジ計算が変になるのを防ぐためにつくったよ。

# エントリー指値をまく間隔を決める値。前に出した指値より最低 vola×step_setting 分の間隔をあけて指値を出すよ。
# 上記のvola_settingを小さくしてる場合、小刻みに大量の指値をまくことになるので、ここを調整して間隔を広げるなどすると良いかも。
step_setting = 1  # 大きくするにつれ指値の間隔が広がるよ。volaが大きくなると勝手に指値間隔は広がることは考慮しておいてね。
step_exit = 0.8  # 利確値幅をvola×step_exitで計算するよ。0だとvolaに関係なく利益になる壁板の手前に指値を出すよ。

# このBotは指値を大きめの板の2円前に出すの。その大きめの板を決める値。
bigvol = 0.1  # デフォルトだと5枚以上の板の2円前に出すよ。ポジション頻度を減らしたかったら10とかに増やすのもあり。
wid = 100  # 大き目の板を中心値から探す数。多くすると遠くの壁板を見つけて指値出せるけど、処理速度が遅くなるかも。

entryvol = bigvol


# これらの設定値次第で運用方法が結構変わると思う。
# 必要に応じてカスタマイズしてみてほしい。相談に乗るから言ってねー。
# --------------------------------------------------


# ※ここから下は触らない方がいいよ！気になることがあったら聞いてね。
# --------------------------------------------------
# 変数定義
board = dict(last=0, bid=0, bsize=0, ask=0, asize=0)
mybtc = 0
entry_price = 0
posside = ''
size = 0
err_FxWs = 0
obp = 9999999
osp = 0


err_SpotWs = 0
spot_price = 0

Time, Open, High, Low, Close, Vol = [], [], [], [], [], []
candle = 0
candlelen = 0
topbeard = 0
underbeard = 0
candleSign = 0
candleList = []
candlelenList = []
candleSignList = []
topbeardList = []
underbeardList = []
vola = 0
volaList = []
range_max = 0
range_max2 = 0
range_min = 9999999
range_min2 = 9999999
range_width = 0
range_center = 0
range_centerList = []
break_up_price = 9999999
break_up_priceList = [9999999 for i in range(10)]
break_down_price = 0
break_down_priceList = [0 for i in range(10)]
b_signal = 0

last = 0
possideList = ['']
poschangetime = datetime.today()
lp = 0
relp = 0
break_flg = 0
exit_id = ''
exit_size = 0

sleep_flg = 0
sleep_order_flg = 0

sizealert_count = 0

expantion_flg = 0
entry_expantion = 0
obc = 0
osc = 0
buy_status = dict(side='', id='', size=0, price=9999999)
sell_status = dict(side='', id='', size=0, price=0)
exit_status = dict(side='', id='', size=0, price=0, possize=0, pos_price=0)
obpList = dict()
ospList = dict()
order_count = sizemax // sizemin

over_limit_time = datetime.today() - timedelta(minutes=1)
ref = 0

err_matilda = 0

collateralList = []

# --------------------------------------------------

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


def line_notify(message, token):
    data = {'message': message}
    headers = {'Authorization': 'Bearer ' + token}
    try:
        requests.post(LINE_NOTIFY_API_URL, data=data, headers=headers)
    except Exception as e:
        print('LINE notify error:', e.args)


def priprint(msg):
    print(msg)
    if discord_flg == 1:
        info_discord(msg, WHURL_a)
    if line_flg == 1 and 'everyone' in msg:
        line_notify(msg, LINE_NOTIFY_TOKEN)

def priprint(msg):
    print(msg)
    if discord_flg == 1:
        info_discord(msg, WHURL_r)
    if line_flg == 1 and 'everyone' in msg:
        line_notify(msg, LINE_NOTIFY_TOKEN)

def lot_calc(ratio, count):
    global sizemin, sizemax, sizebreak, sizealert, order_count
    try:
        collateral = api.getcollateral()['collateral']
        collateralList.append(collateral)
        msgList = []
        if len(collateralList) <= 1:
            msg = '{} collateral:\\{}'.format(datetime.today(), str(collateral))
            msgList.append(msg)
        else:
            msg = '{} collateral:\\{} → {} ({})'.format(datetime.today(), str(collateralList[-2]), str(collateralList[-1]),
                                                   str(collateralList[-1] - collateralList[-2]))
            msgList.append(msg)
        '''if len(collateralList) <= 1 or collateralList[-1] < collateralList[-2]:'''
        minimum_require = last / leverage * 0.01
        max_lot = collateral / minimum_require * 0.01 * ratio
        sizemin = round(max_lot / count, 8)
        sizemax = round(sizemin * count, 8)
        sizealert = sizemin * alert_ratio
        order_count = count
        if sizemin < 0.01:
            priprint('@everyone Game Over')
            sys.exit()
        msg = '                           sizemin:{} sizemax:{}'.format(str(sizemin), str(sizemax))
        msgList.append(msg)
        msg = '\n'.join(msgList)
        priprint(msg)
    except Exception as e:
        print('lot calc error', e.args)


# --------------------------------------------------
# 時間計測とポジション情報取得
def fetch_current(x):
    global sleep_flg
    while True:
        if (datetime.now().hour == 23 or datetime.now().hour == 3) \
                and datetime.now().minute >= 50:
            if sleep_flg == 0:
                sleep_flg = 1
                cancel_allorders()
                priprint('{} sleep mode'.format(datetime.today()))
            elif (datetime.now().hour == 23 or datetime.now().hour == 3) \
                    and datetime.now().minute >= 58:
                if mybtc != 0:
                    reflesh()
        elif (datetime.now().hour == 0 and datetime.now().minute == 0 and sleep_flg == 1) \
                or (datetime.now().hour == 4 and datetime.now().minute == 15 and sleep_flg == 1):
            sleep_flg = 0
            priprint('{} wake up'.format(datetime.today()))
        if datetime.now().minute % foot == 0 and datetime.now().second == x:
            global error
            error = 0
            break
        time.sleep(0.5)


def fetch_bf():
    global mybtc, entry_price, posside
    while True:
        try:
            global position, orders
            position = api.getpositions(product_code='FX_BTC_JPY')
            # orders = api.getchildorders(product_code='FX_BTC_JPY', child_order_state='ACTIVE')
            try:
                posside = position[0]['side']
                possideList.append(posside)
                mybtc = round(sum([position[i]['size'] for i in range(len(position))]), 8)
                entry_price = round(
                    sum([position[i]['price'] * position[i]['size'] for i in range(len(position))]) / mybtc)
            except Exception as e:
                mybtc = 0
                entry_price = 0
                posside = 'None'
                possideList.append(posside)
            break
        except Exception as e:
            priprint('infomation error from bitflyer retry after 15 sec.')
            time.sleep(10)


def pripara():
    global entry_price, sizealert_count
    bup = break_up_priceList[-break_delay] if break_up_priceList[-break_delay] > range_max2 else range_max2
    bdp = break_down_priceList[-break_delay] if break_down_priceList[-break_delay] < range_min2 else range_min2
    msg = ('--------------------------------------------------------------------------------\n'
           ' {} \\{} candle : {} beard top : {} under : {}\n'
           ' [vol] {} [vol_ave] {} [volatility] {} \n'
           ' [range] high-low : {}-{}({}) center : {}\n'
           ' [range2] high-low : {}-{}\n'
           ' [break price] up : {} down : {}\n'
           ' [position] {} {}btc \\{} since {}\n'
           ' [flg] expantion:{} break:{} b_signal:{} sleep:{}\n'
           '--------------------------------------------------------------------------------'.format(
        str(Time[-1]),
        str(Close[-1]),
        str(candle),
        str(topbeard),
        str(underbeard),
        str(round(Vol[-1])),
        str(round(vol_ave)),
        str(round(vola)),
        str(range_max),
        str(range_min),
        str(range_width),
        str(range_center),
        str(range_max2),
        str(range_min2),
        str(bup),
        str(bdp),
        posside,
        str(mybtc),
        str(entry_price),
        str(poschangetime),
        str(expantion_flg),
        str(break_flg),
        str(b_signal),
        str(sleep_flg)
    ))
    if mybtc >= sizealert and sizealert_count < sizealert_limit:
        msgList = []
        msgList.append(msg)
        #msgList.append('@everyone !alert! position size expand')
        msgList.append('!alert! position size expand')
        msg = '\n'.join(msgList)
        sizealert_count += 1
    elif mybtc < sizealert:
        sizealert_count = 0
    priprint(msg)

    return


# ローソク足の取得と判定

def get_candle_first(foot):
    global candle, topbeard, underbeard, candleSign, candlelen, vola, b_signal, vol_ave, \
        range_max, range_max2, range_min, range_min2, range_width, range_center, break_up_price, break_down_price, expantion_flg
    unixTime = lambda y, m, d, h, minu: int(time.mktime(datetime(y, m, d, h, minu).timetuple()))
    now = datetime.today()
    after = now - timedelta(minutes=range_count*5)
    y, m, d, h, minu = now.year, now.month, now.day, now.hour, now.minute
    ay, am, ad, ah, aminu = after.year, after.month, after.day, after.hour, after.minute
    periods = 60 * int(foot)
    url = 'https://api.cryptowat.ch/markets/bitflyer/btcfxjpy/ohlc'
    query = {
        'periods': periods,  # 60→1分足　3600→1時間足　日足→86400
        'before': unixTime(y, m, d, h, minu),
        'after': unixTime(ay, am, ad, ah, aminu),
    }
    data = requests.get(url, params=query).json()['result'][str(periods)]
    for i in data:
        Time.append(datetime.fromtimestamp(i[0]))
        Open.append(i[1])
        High.append(i[2])
        Low.append(i[3])
        Close.append(i[4])
        Vol.append(i[5])
        candle = Close[-1] - Open[-1]
        candleList.append(candle)
        candlelen = abs(candle)
        candlelenList.append(candlelen)
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
            if topbeard > beard_ignore:
                High[-1] = Close[-1]
            if underbeard > beard_ignore:
                Low[-1] = Open[-1]
        elif candleSign == -1:
            topbeard = High[-1] - Open[-1]
            underbeard = Close[-1] - Low[-1]
            if topbeard > beard_ignore:
                High[-1] = Open[-1]
            if underbeard > beard_ignore:
                Low[-1] = Close[-1]
        else:
            topbeard = High[-1] - Open[-1]
            underbeard = Close[-1] - Low[-1]
            if topbeard > beard_ignore:
                High[-1] = Close[-1]
            if underbeard > beard_ignore:
                Low[-1] = Open[-1]
        if High[-1] > range_max and candleSign == 1:
            expantion_flg += 1
        elif Low[-1] < range_min and candleSign == -1:
            expantion_flg -= 1
        elif (expantion_flg >= 1 and Low[-1] < range_center) or expantion_flg <= -1 and High[-1] > range_center:
            expantion_flg = 0
        if len(Time) > range_count:
            topbeardList.append(topbeard)
            underbeardList.append(underbeard)
            cl = candlelenList[-vola_count:-1]
            vola = sum(cl) / vola_count
            volaList.append(vola)
            h = High[-range_count:]
            range_max = max(h)
            h2 = High[-range_count*2:]
            range_max2 = max(h2)
            l = Low[-range_count:]
            range_min = min(l)
            l2 = Low[-range_count*2:]
            range_min2 = min(l2)
            range_width = range_max - range_min
            range_center = round((range_max + range_min) / 2)
            range_centerList.append(range_center)
            #if expantion_flg == 0 or break_flg != 0:
            #if abs(expantion_flg) <= 5 or break_flg != 0:
            if range_max != range_max2 or break_flg != 0:
                break_up_price = range_max + range_width / 2
                break_up_priceList.append(break_up_price)
            if range_min != range_min2 or break_flg != 0:
                break_down_price = range_min - range_width / 2
                break_down_priceList.append(break_down_price)
            vl = Vol[-vola_count:-1]
            vol_ave = sum(vl) / vola_count
            if Vol[-1] > vol_ave and break_flg != 0:
                if topbeard > underbeard and topbeard > candlelen:
                    if break_flg == 1 and b_signal >= 0:
                        b_signal -= 1
                    elif break_flg == -1:
                        b_signal = -1
                elif underbeard > topbeard and underbeard > candlelen:
                    if break_flg == -1 and b_signal <= 0:
                        b_signal += 1
                    elif break_flg == 1:
                        b_signal = 1
                elif candleSign == -1:
                    if break_flg == 1 and b_signal >= 0:
                        b_signal -= 1
                    elif break_flg == -1:
                        b_signal = -1
                elif candleSign == 1:
                    if break_flg == -1 and b_signal <= 0:
                        b_signal += 1
                    elif break_flg == 1:
                        b_signal = 1
            elif b_signal != 0 and expantion_flg == 0:
                b_signal = 0

def get_candle(foot):
    global candle, topbeard, underbeard, candleSign, candlelen, vola, b_signal, vol_ave, \
        range_max, range_max2, range_min, range_min2, range_width, range_center, break_up_price, break_down_price, expantion_flg
    unixTime = lambda y, m, d, h, minu: int(time.mktime(datetime(y, m, d, h, minu).timetuple()))
    now = datetime.today()
    after = now - timedelta(minutes=foot)
    y, m, d, h, minu = now.year, now.month, now.day, now.hour, now.minute
    ay, am, ad, ah, aminu = after.year, after.month, after.day, after.hour, after.minute
    periods = 60 * int(foot)
    url = 'https://api.cryptowat.ch/markets/bitflyer/btcfxjpy/ohlc'
    query = {
        'periods': periods,  # 60→1分足　3600→1時間足　日足→86400
        'before': unixTime(y, m, d, h, minu),
        'after': unixTime(ay, am, ad, ah, aminu),
    }
    try:
        data = requests.get(url, params=query).json()['result'][str(periods)]
        Time.append(datetime.fromtimestamp(data[-1][0]))
        Open.append(data[-1][1])
        High.append(data[-1][2])
        Low.append(data[-1][3])
        Close.append(data[-1][4])
        Vol.append(data[-1][5])
        candle = Close[-1] - Open[-1]
        candleList.append(candle)
        candlelen = abs(candle)
        candlelenList.append(candlelen)
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
            if topbeard > beard_ignore:
                High[-1] = Close[-1]
            if underbeard > beard_ignore:
                Low[-1] = Open[-1]
        elif candleSign == -1:
            topbeard = High[-1] - Open[-1]
            underbeard = Close[-1] - Low[-1]
            if topbeard > beard_ignore:
                High[-1] = Open[-1]
            if underbeard > beard_ignore:
                Low[-1] = Close[-1]
        else:
            topbeard = High[-1] - Open[-1]
            underbeard = Close[-1] - Low[-1]
            if topbeard > beard_ignore:
                High[-1] = Close[-1]
            if underbeard > beard_ignore:
                Low[-1] = Open[-1]
        if High[-1] > range_max:
            expantion_flg += 1
        elif Low[-1] < range_min:
            expantion_flg -= 1
        elif (expantion_flg >= 1 and Low[-1] < range_center) or expantion_flg <= -1 and High[-1] > range_center:
            expantion_flg = 0
        topbeardList.append(topbeard)
        underbeardList.append(underbeard)
        cl = candlelenList[-vola_count:-1]
        vola = sum(cl) / vola_count
        volaList.append(vola)
        h = High[-range_count:]
        range_max = max(h)
        h2 = High[-range_count * 2:]
        range_max2 = max(h2)
        l = Low[-range_count:]
        range_min = min(l)
        l2 = Low[-range_count * 2:]
        range_min2 = min(l2)
        range_width = range_max - range_min
        range_center = round((range_max + range_min) / 2)
        range_centerList.append(range_center)
        if range_max != range_max2 or break_flg != 0:
            break_up_price = range_max + range_width / 2
            break_up_priceList.append(break_up_price)
        if range_min != range_min2 or break_flg != 0:
            break_down_price = range_min - range_width / 2
            break_down_priceList.append(break_down_price)
        vl = Vol[-vola_count:-1]
        vol_ave = sum(vl) / vola_count
        if Vol[-1] > vol_ave and break_flg != 0:
            if topbeard > underbeard and topbeard > candlelen:
                if break_flg == 1 and b_signal >= 0:
                    b_signal -= 1
                elif break_flg == -1:
                    b_signal = -1
            elif underbeard > topbeard and underbeard > candlelen:
                if break_flg == -1 and b_signal <= 0:
                    b_signal += 1
                elif break_flg == 1:
                    b_signal = 1
            elif candleSign == -1:
                if break_flg == 1 and b_signal >= 0:
                    b_signal -= 1
                elif break_flg == -1:
                    b_signal = -1
            elif candleSign == 1:
                if break_flg == -1 and b_signal <= 0:
                    b_signal += 1
                elif break_flg == 1:
                    b_signal = 1
        elif b_signal != 0 and expantion_flg == 0:
            b_signal = 0
    except Exception as e:
        msg = 'error by cryptowatch'
        print(msg)


# 注文処理

def cancel_allorders():
    global buy_status, sell_status, exit_status, obc, osc, obpList, ospList, entry_expantion
    while True:
        res = api.cancelallchildorders(product_code='FX_BTC_JPY')
        if 'error' in str(res):
            print('{} error occurred, retry CANCEL' + str(res).format(datetime.today()))
            time.sleep(0.5)
        else:
            break
    buy_status = dict(side='', id='', size=0, price=9999999)
    sell_status = dict(side='', id='', size=0, price=0)
    exit_status = dict(side='', id='', size=0, price=0, possize=0, pos_price=0)
    obc = 0
    osc = 0
    obpList = dict()
    ospList = dict()
    entry_expantion = 0
    print('{} all order canceled'.format(datetime.today()))
    time.sleep(0.6)


def order_market(size, buy=True):
    while True:
        if buy:
            side = 'BUY'
        else:
            side = 'SELL'
        res = api.sendchildorder(product_code='FX_BTC_JPY', child_order_type='MARKET', side=side, size=size)
        if 'acceptance' in str(res):
            print('{} MARKET {} size:{} {}'.format(datetime.today(), side, str(size), str(res)))
            return res['child_order_acceptance_id']
        else:
            order_error_catch(res)
            return ''


def order_limit(size, price, buy=True):
    while True:
        if buy:
            side = 'BUY'
        else:
            side = 'SELL'
        res = api.sendchildorder(product_code='FX_BTC_JPY', child_order_type='LIMIT', side=side, size=size,
                                 price=price)
        if 'acceptance' in str(res):
            print('{} LIMIT {} size:{} price:{} {}'.format(datetime.today(), side, str(size), str(price), str(res)))
            return res['child_order_acceptance_id']
        else:
            order_error_catch(res)
            return ''


def reflesh():
    global ref
    if ref == 0:
        api.cancelallchildorders(product_code='FX_BTC_JPY')
        time.sleep(3)
    if posside == 'BUY':
        res = order_market(mybtc, buy=False)
    else:
        res = order_market(mybtc, buy=True)
    if res != '':
        ref = 1
    time.sleep(3)


def order_error_catch(response):
    if response['error_message'] == 'Margin amount is insufficient for this order.':
        print('{} Margin amount error occurred, other orders cancel and retry'.format(datetime.today()))
        cancel_allorders()
        return ''
    if response['error_message'] == 'Over API limit per minute':
        print('{} Over API limit'.format(datetime.today()))
        global over_limit_time
        over_limit_time = datetime.today()
        return ''
    if response['error_message'] == 'The minimum order size is 0.01 BTC.':
        print('{} minimum size error'.format(datetime.today()))
        return ''


# WS

class FxWs(object):

    def __init__(self):
        global board
        self.ws = websocket.WebSocketApp(
            'wss://ws.lightstream.bitflyer.com/json-rpc', header=None,
            on_open=self.on_open, on_message=self.on_message,
            on_error=self.on_error, on_close=self.on_close)

    def on_open(self, ws):
        global err_FxWs
        ws.send(json.dumps({'method': 'subscribe',
                            'params': {'channel': 'lightning_board_snapshot_FX_BTC_JPY'}}))
        print('{} Fx web-socket connected'.format(datetime.today()))
        err_FxWs = 0

    def on_error(self, ws, error):
        self.ws.close()

    def on_close(self, ws):
        global err_FxWs
        err_FxWs = 1
        pass

    def on_message(self, ws, message):
        global last, break_flg, entry_flg, poschangetime, sleep_flg
        message = json.loads(message)['params']
        board['bid'] = [message['message']['bids'][i]['price'] for i in range(wid)]
        board['bsize'] = [message['message']['bids'][i]['size'] for i in range(wid)]
        board['ask'] = [message['message']['asks'][i]['price'] for i in range(wid)]
        board['asize'] = [message['message']['asks'][i]['size'] for i in range(wid)]
        board['last'] = message['message']['mid_price']
        last = board['last']

    def run(self):
        threading.Thread(target=lambda: self.ws.run_forever(), daemon=True).start()

    def get_board(self):
        return board

class SpotWs(object):

    def __init__(self):
        global spot_price
        self.ws = websocket.WebSocketApp(
            'wss://ws.lightstream.bitflyer.com/json-rpc', header=None,
            on_open=self.on_open, on_message=self.on_message,
            on_error=self.on_error, on_close=self.on_close)

    def on_open(self, ws):
        global err_SpotWs
        ws.send(json.dumps({'method': 'subscribe',
                            'params': {'channel': 'lightning_executions_BTC_JPY'}}))
        print('{} Spot web-socket connected'.format(datetime.today()))
        err_SpotWs = 0

    def on_error(self, ws, error):
        self.ws.close()

    def on_close(self, ws):
        global err_SpotWs
        err_SpotWs = 1
        pass

    def on_message(self, ws, message):
        global spot_price
        message = json.loads(message)['params']
        spot_price = message['message'][0]['price']

    def run(self):
        threading.Thread(target=lambda: self.ws.run_forever(), daemon=True).start()

    def get_spot_price(self):
        return spot_price

# manager class
class Matilda(threading.Thread):
    def __init__(self):
        global err_matilda
        super(Matilda, self).__init__()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

        self.entry_flg = 0
        self.entry_expantion = 0
        self.exit_flg = 0
        err_matilda = 0
        priprint('{} matilda open'.format(datetime.today()))

    def sfd_calc(self, sp, fp):
        sfd = (fp - sp) / sp * 100 if sp != 0 else 0
        return sfd

    def order_buy(self):
        global obc, buy_status, entryvol
        step = vola * step_setting
        if break_flg == 0 or obc == 0:
            entryvol = bigvol
        else:
            entryvol = sizemin
        if mybtc < sizemax:
            if posside == 'BUY' and obc == 0:
                buy_status = dict(side='BUY', id='', size=mybtc, price=entry_price)
                obpList[obc] = buy_status
                obc += mybtc // sizemin
            for i in range(wid):
                if board['bsize'][i] > entryvol:
                    price = board['bid'][i] + 2
                    if price < buy_status['price'] - step and obc < order_count:
                        id = order_limit(sizemin, price, buy=True)
                        if id != '':
                            buy_status = dict(side='BUY', id=id, size=sizemin, price=price)
                            obpList[obc] = buy_status
                            obc += 1
                            time.sleep(0.6)
                        break
                    elif posside == 'None' and obc != 0 and price > obpList[0]['price']:
                        cancel_allorders()
                        break

    def order_sell(self):
        global osc, sell_status, entryvol
        step = vola * step_setting
        entryvol = bigvol
        if mybtc < sizemax:
            if posside == 'SELL' and osc == 0:
                sell_status = dict(side='SELL', id='', size=mybtc, price=entry_price)
                ospList[osc] = sell_status
                osc += mybtc // sizemin
            for i in range(wid):
                if board['asize'][i] > entryvol:
                    price = board['ask'][i] - 2
                    if price > sell_status['price'] + step and osc < order_count:
                        id = order_limit(sizemin, price, buy=False)
                        if id != '':
                            sell_status = dict(side='SELL', id=id, size=sizemin, price=price)
                            ospList[osc] = sell_status
                            osc += 1
                            time.sleep(0.6)
                        break
                    elif posside == 'None' and osc != 0 and price < ospList[0]['price']:
                        cancel_allorders()
                        break

    def order_exit(self):
        global exit_status
        exit_vola = vola * step_exit * (sizemin / mybtc)
        price = 0
        size = mybtc
        exitvol = bigvol
        if posside == 'SELL':
            side = 'BUY'
            buy = True
            sign = 1
            if sleep_flg == 1 or self.exit_flg == 1:
                for i in range(wid):
                    if board['bsize'][i] > exitvol:
                        price = board['bid'][i]
                        if price < entry_price-exit_vola*sign:
                            break
                        else:
                            price = 0
            elif self.exit_flg == 2:
                price = range_center if range_center > entry_price-exit_vola*sign else entry_price-exit_vola*sign
        elif posside == 'BUY':
            side = 'SELL'
            buy = False
            sign = -1
            if sleep_flg == 1 or self.exit_flg == 1:
                for i in range(wid):
                    if board['asize'][i] > exitvol:
                        price = board['ask'][i]
                        if price > entry_price - exit_vola*sign:
                            break
                        else:
                            price = 0
            elif self.exit_flg == 2:
                price = range_center if range_center < entry_price-exit_vola*sign else entry_price-exit_vola*sign
        if price == 0:
            pass
        elif exit_status['id'] != '' and ((exit_status['size'] != size or exit_status['side'] == posside)
                                          or (exit_status['side'] == 'BUY' and price > exit_status['price'])
                                          or (exit_status['side'] == 'SELL' and price < exit_status['price'])
                                          or exit_status['possize'] != mybtc
                                          or exit_status['pos_price'] != entry_price):
            res = api.cancelchildorder(product_code='FX_BTC_JPY', child_order_acceptance_id=exit_status['id'])
            print('{} exit canceled'.format(datetime.today(), str(res)))
            exit_status = dict(side='', id='', size=0, price=0, possize=0, pos_price=0)
        elif size >= 0.01 and price > 0:
            if exit_status['id'] == '':
                id = order_limit(size, price, buy)
                if id != '':
                    exit_status = dict(side=side, id=id, size=size, price=price, possize=mybtc, pos_price=entry_price)
                    print('{} exit submitted'.format(datetime.today()))

    def break_judge(self):
        global break_flg
        if break_delay != 0:
            bup = break_up_priceList[-break_delay] if break_up_priceList[-break_delay] > range_max2 else range_max2
            bdp = break_down_priceList[-break_delay] if break_down_priceList[-break_delay] < range_min2 else range_min2
            if bup < board['bid'][0] and break_flg != 1 and b_signal != -1:
                break_flg = 1
                '''if posside == 'SELL':
                    reflesh()
                else:
                    cancel_allorders()'''
                priprint('@everyone {} breaking up!!!'.format(datetime.today()))
                #priprint('{} breaking up!!!'.format(datetime.today()))
            elif bdp > board['ask'][0] and break_flg != -1 and b_signal != 1:
                break_flg = -1
                '''if posside == 'BUY':
                    reflesh()
                else:
                    cancel_allorders()'''
                priprint('@everyone {} breaking down!!!'.format(datetime.today()))
                #priprint('{} breaking down!!!'.format(datetime.today()))

    def break_off_judge(self):
        global break_flg, b_signal
        if break_flg == 1:
            if last < range_center:
                priprint('@everyone {} breaking off'.format(datetime.today()))
                #priprint('{} breaking off'.format(datetime.today()))
                break_flg = 0
                b_signal = 0
        if break_flg == -1:
            if last > range_center:
                priprint('@everyone {} breaking off'.format(datetime.today()))
                #priprint('{} breaking off'.format(datetime.today()))
                break_flg = 0
                b_signal = 0

    def ently_judge(self):
        sfd = self.sfd_calc(spot_price, last)
        self.break_judge()
        if sleep_flg == 1:
            self.entry_flg = 0
        elif 4.8 < sfd < 5.2:
            self.entry_flg = 0
        elif 5.2 <= sfd:
            if break_flg == 0:
                if range_width < range_setting or range_width > over_range_setting:
                    self.entry_flg = 0
                elif last > range_center + vola * entry_setting:
                    self.entry_flg = -1
                elif last < range_center - vola * entry_setting:
                    self.entry_flg = 0
                else:
                    self.entry_flg = 0
            else:
                if break_flg == -b_signal:
                    self.entry_flg = 0
                elif break_flg == -1:
                    self.entry_flg = break_flg
                else:
                    self.entry_flg = 0
        else:
            if break_flg == 0:
                if range_width < range_setting or range_width > over_range_setting:
                    self.entry_flg = 0
                elif last > range_center + vola * entry_setting:
                    self.entry_flg = -1
                elif last < range_center - vola * entry_setting:
                    self.entry_flg = 1
                else:
                    self.entry_flg = 0
            else:
                if break_flg == -b_signal or (b_signal == 0 and posside == 'None'):
                    self.entry_flg = 0
                else:
                    self.entry_flg = break_flg

    def exit_judge(self):
        if break_flg == 0:
            if posside == 'SELL':
                if self.entry_flg == 1 or (datetime.today() > poschangetime + timedelta(minutes=alert_count * 2)):
                    self.exit_flg = 3
                elif (datetime.today() > poschangetime + timedelta(minutes=alert_count)) \
                        or entry_price < range_center:
                    self.exit_flg = 2
                else:
                    self.exit_flg = 1
            elif posside == 'BUY':
                if self.entry_flg == -1 or (datetime.today() > poschangetime + timedelta(minutes=alert_count * 2)):
                    self.exit_flg = 3
                elif (datetime.today() > poschangetime + timedelta(minutes=alert_count)) \
                        or entry_price > range_center:
                    self.exit_flg = 2
                else:
                    self.exit_flg = 1
            else:
                self.exit_flg = 0
        elif (posside == 'BUY' and self.entry_flg == -1) or (posside == 'SELL' and self.entry_flg == 1):
            self.exit_flg = 3
        elif b_signal == 0:
            self.exit_flg = 1
        elif break_flg == -b_signal:
            self.exit_flg = 2
        elif mybtc >= breakexitsize * sizemin:
            self.exit_flg = 1
        else:
            self.exit_flg = 0


    def run(self):
        global poschangetime, ref, break_flg
        while not self.stop_event.is_set():
            try:
                # ポジション管理
                fetch_bf()
                if 0.01 > mybtc > 0:
                    if posside == 'BUY':
                        order_market(0.01, buy=True)
                    elif posside != 'BUY':
                        order_market(0.01, buy=False)
                if possideList[-1] != possideList[-2]:
                    if possideList[-1] == 'None':
                        cancel_allorders()
                        self.entry_expantion = 0
                        self.exit_flg = 0
                        if ref == 1:
                            ref = 0
                            print('{} refleshed'.format(datetime.today()))
                        if fukuri == 1:
                            if expantion_flg == 0:
                                lot_calc(collateral_using, 5)
                            else:
                                lot_calc(collateral_using, 7)
                            time.sleep(0.6)
                    else:
                        self.entry_expantion = expantion_flg
                    poschangetime = datetime.today()
                    priprint('{} posside changed {} to {}'.format(poschangetime, possideList[-2], possideList[-1]))
                elif ref == 1 and posside == 'None':
                    self.entry_expantion = 0
                    self.exit_flg = 0
                    ref = 0
                    print('{} refleshed'.format(datetime.today()))
                # WEBソケット再接続
                if err_FxWs == 1:
                    fxws = FxWs()
                    fxws.run()
                if err_SpotWs == 1:
                    spotws = SpotWs()
                    spotws.run()
                # 注文処理
                if datetime.today() > over_limit_time + timedelta(minutes=1):
                    self.ently_judge()
                    if self.entry_flg == 1:
                        if osc != 0 and mybtc == 0:
                            cancel_allorders()
                        self.order_buy()
                    if self.entry_flg == -1:
                        if obc != 0 and mybtc == 0:
                            cancel_allorders()
                        self.order_sell()
                    if self.entry_flg == 0:
                        if obc != 0 or osc != 0 and mybtc == 0:
                            cancel_allorders()
                    if mybtc >= 0.01:
                        self.exit_judge()
                        if self.exit_flg == 3:
                                priprint('@everyone {} see ya to idiot position'.format(datetime.today()))
                                reflesh()
                        elif self.exit_flg != 0:
                            self.order_exit()
                if break_flg != 0:
                    self.break_off_judge()
            except Exception as e:
                global err_matilda
                err_matilda = 1
                priprint('@everyone {} matilda error {}'.format(datetime.today(), e.args))
                self.stop()
                break
            time.sleep(0.6)

    def stop(self):
        self.stop_event.set()
        #self.thread.join()
        priprint('{} matilda close'.format(datetime.today()))


def main():
    # --------------------------------------------------
    # 起動メッセージ
    priprint('--------------------------------------------------------------')
    priprint('                      martin start')
    priprint('--------------------------------------------------------------')

    fetch_bf()
    get_candle_first(foot)
    pripara()
    cancel_allorders()

    # --------------------------------------------------

    # 初回起動
    fxws = FxWs()
    fxws.run()
    spotws = SpotWs()
    spotws.run()
    time.sleep(10)
    if fukuri == 1:
        lot_calc(collateral_using, pos_count)
    matilda = Matilda()
    # 以下ループ

    try:
        while True:
            fetch_current(1)
            get_candle(foot)
            pripara()
            time.sleep(0.5)
            if err_matilda == 1:
                matilda = Matilda()
    except KeyboardInterrupt:
        cancel_allorders()
        matilda.stop()
        sys.exit()
        pass


if __name__ == '__main__':
    main()
