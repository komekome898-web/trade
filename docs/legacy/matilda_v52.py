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
import pandas
import dateutil.parser
from collections import deque
import warnings

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
#    利確に板を使う仕様に変更 利確値幅を決められる様に変更(exit_step)
#    複利ロット計算機能を追加                                                                                       2019/06/09
#
# 37 なんやかんやあって落ち着いて運用できる形になったもの
#    さらに変更されたbfAPI/cwAPIの制限に対応
#    sizeminを基準にポジ数によって利確値幅(vola*exit_step)を按分して、決済時の収益性を平滑化
#    break時の仕様を変化
#     ・倍のレンジの高値安値以内はブレイクにしない
#     ・ブレイク方向のポジでナンピン
#     ・出来高のある逆行を検知して利確指値を出す 二回連続の逆行でポジブン投げ、順行するまで一旦エントリー停止
#     ・breakexitsizeで指定したポジ数までは利確指値を出さない（たまに数万幅とかとれる）
#    ※懸念点
#    　bfAPIが返してくるエラーで意味わからんのがあって、そんときは止めて時間おいて起動しなおす手間がいる                               2019/09/04
# 38 頻発したAPIエラーに対応
#    利確のタイミングや方法を選べるように変更（exit_mode）
#    ブレイク時はスキャに専念しブレイクオフ判断を早める仕様に変更
#    強制損切りを成行連打仕様に変更                                                                                 2019/10/30
# 41 ブレイク削除タイプの真性逆張りナンピン仕様
#    vr (range_width/vola) を指標にロットとエントリー/利確ポイントを変える仕様に変更                                          2020/02/04
# 51 time_anomalyを1にすると、時刻トレードの逆ポジはとらず、順ポジをとった場合は時間がくるまで利確・損切りしない
#    スリープ時間に0-2時 7-8時 19-20時を追加
#    sfd下乖離に対応                                                                                              2020/03/21           
# 52 over_sleepを1にすると、スリープ時間に0-2時 7-8時 19-20時に寝るように変更
#    時刻トレード時は建値+レンジ幅で利確指示を出すように変更（雑）
#    エントリー指値の秒間隔order_delayをinnnerとouterに追加。デフォルト値は雑                                               2020/04/04 
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
# 設定値 コメントをよく読んで設定してね。

# --------------------------------------------------
# 41から 不安定なブレイクをやめて、レンジ幅÷ボラ　の数値でトレンド検知するようになりました。（雑に vr って名づけてます。）
# vrが大きくなれば一方的なトレンドって判断します。
# ここで vr_setting って設定値を用意し、vrの大小で挙動を変えるようにしてます。
# 例えばデフォルトだと、vr>10のときはヒゲ狙いで逆張り、vr<10のときはレンジ内で細かくポジ取って損切りはしない。って感じ。
#

settings_inner = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
vr_setting = 100
settings_outer = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)

time_anomaly = 0                                 # 時刻トレードを考慮する場合は1、今までどおり無視する場合は0               
over_sleep = 0                                   # スリープ時間を増やす場合は1、最低限にする場合は0
order_delay = settings_outer['order_delay']      # 前回のエントリー指値から次のエントリー指値を出す最低間隔（秒）
# --------------------------------------------------
entry_setting = settings_outer['entry_setting']  # 大きくするにつれ中央値から離れたところでエントリーするよ。
exit_setting = settings_outer['exit_setting']    # 大きくするにつれ中央値から離れたところで利確するよ。
entry_step = settings_outer['entry_step']        # 大きくするにつれ指値の間隔が広がるよ。volaが大きくなると勝手に指値間隔は広がることは考慮しておいてね。

sizemin = settings_outer['sizemin']              # 最小ロット。このサイズの指値をいっぱいまくよ。
sizemax = settings_outer['sizemax']              # 最大ロット。ポジションがここまで肥大すると注文をやめるよ。許容する証拠金に応じて決めてね。
order_count = settings_outer['order_count']      # ポジの個数。

sizealert = 0.4         # この数値以上のポジを持つとお知らせするよ。毎分するよ。
sizealert_limit = 1     # この回数お知らせするよ。お知らせ自体いらないなら0にしてね。


# 基準時間足。ボラやレンジ幅の計算や、利確指値を出す間隔に影響するよ。一旦デフォルト値のままがオススメ。
foot = 5  # 基準時間足(秒)
vola_count = 6   # foot×この時間分の平均ボラを計算するよ。
range_count = 6  # foot×この時間分のレンジ幅を計算するよ。
alert_count = 1  # (分)この時間分ポジションに変更がなかったらクソポジと判断してアラートがなるよ。
#                             ポジションがレンジ中央値より悪いと、損切指値を出すよ
#                             その後、更にこの時間分持ち続けてたら、損益に関わらず強制決済するよ。
#                             ポジションの回転数をあげたかったらもっと短くしてもいいよ。

# レンジ幅のしきい値設定。どちらかがこの数値以下の場合エントリーをしなくなるよ。ポジポジ病防止の役目をするよ。
range_setting = 100  # レンジ幅がこの数値以下になるとエントリーしなくなるよ。
over_range_setting = 900000  # レンジ幅がこの数値以上になるとエントリーしなくなるよ。

# 利確に関わるもの
exit_mode = 1       # 利確のタイミングを決めるよ。 0:ドテン(ポジと反対のエントリー時) 1:センター付近 2:値幅
exit_step = 0       # 利確値幅をvola×exit_stepで計算するよ。0だとvolaに関係なく利益になる壁板の手前に指値を出すよ。
#                     exit_mode = 2 の時やブレイク時に使うよ。

beard_ignore = 1  # この数値以上の長い髭を無視してレンジ計算するよ。
#                   bfは大口雑成行とmmbotterによるクソ髭によってレンジ計算が変になるのを防ぐためにつくったよ。

# このBotは指値を大きめの板の2円前に出すの。その大きめの板を決める値。
bigvol = 1  # デフォルトだと1枚以上の板の2円前に出すよ。ポジション頻度を減らしたかったら10とかに増やすのもあり。
wid = 200  # 大き目の板を中心値から探す数。多くすると遠くの壁板を見つけて指値出せるけど、処理速度が遅くなるかも。


fukuri = 0  # 1にするとノーポジ時にロットを自動計算するよ。長期複利運用をする人用。いらんなら0にしてね。
leverage = 4  # レバだよ
collateral_using = 0.95  # 証拠金の何割使うかだよ。
pos_count = 5  # sizemin何個分のポジを最大もつかきめるよ（sizemax）
alert_ratio = 10  # sizemin何個分のポジでアラートするかきめるよ（sizealert）

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
entryvol = bigvol

err_SpotWs = 0
spot_price = 0
health = ''

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
vol_ave = 0
range_max = 0
range_min = 9999999
range_width = 0
range_center = 0
range_centerList = []
HP = 0
LP = 0
vr = 0
vrList = []

last = 0
possideList = ['']
poschangetime = datetime.today()
exit_id = ''
exit_size = 0

sleep_flg = 0

sizealert_count = 0

obc = 0
osc = 0
buy_status = dict(side='', id='', size=0, price=9999999)
sell_status = dict(side='', id='', size=0, price=0)
exit_status = dict(side='', id='', size=0, price=0, possize=0, pos_price=0)
obpList = dict()
ospList = dict()

ssp = 9999999
lsp = 0
sep = 9999999
lep = 0
ep = 0

winc = 0
losec = 0
rensho = 0
renpai = 0
winmoneyList = []
losemoneyList = []

over_limit_time = datetime.today() - timedelta(minutes=1)
ref = 0

err_matilda = 0
err_time = datetime.today()
collateralList = []

sfd_mode = 0

anomaly_flg = 0

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

def lot_calc(ratio, count):
    global sizemin, sizemax, sizebreak, sizealert, order_count, rensho, renpai, winc, losec
    try:
        rratio = ratio
        collateral = api.getcollateral()['collateral']
        time.sleep(0.6)
        collateralList.append(collateral)
        msgList = []
        coldel = collateralList[-1] - collateralList[-2]
        if len(collateralList) <= 1:
            msg = '{} collateral:\\{}'.format(datetime.today(), str(collateral))
            msgList.append(msg)
        else:
            msg = '{} collateral:\\{} → {} ({})'.format(datetime.today(), str(collateralList[-2]), str(collateralList[-1]),
                                                   str(coldel))
            if coldel != 0:
                msgList.append(msg)
                if coldel > 0:
                    rensho += 1
                    renpai = 0
                    winc += 1
                    winmoneyList.append(coldel)
                else:
                    renpai -= 1
                    rensho = 0
                    losec += 1
                    losemoneyList.append(coldel)
        '''if len(collateralList) <= 1 or collateralList[-1] < collateralList[-2]:'''
        minimum_require = last / leverage * 0.01
        if rensho >= 1:
            rratio = ratio -(rensho*0.05)
            if rratio < 0.9:
                rratio = 0.9
        max_lot = collateral / minimum_require * 0.01 * rratio
        sizemin = round(max_lot / count, 8)
        if sizemin < 0.01:
            sizemin = 0.01
        sizemax = round(sizemin * count, 8)
        sizealert = sizemin * alert_ratio
        order_count = count
        if sizemin < 0.01:
            priprint('@everyone Game Over')
            sys.exit()
        msg = '         rensho:{} sizemin:{} sizemax:{}'.format(str(rensho),str(sizemin), str(sizemax))
        msgList.append(msg)
        msg = '\n'.join(msgList)
        priprint(msg)
    except Exception as e:
        print('lot calc error', e.args)


# --------------------------------------------------
# 時間計測とポジション情報取得

def anomaly_judge():
    global anomaly_flg
    if (datetime.now().weekday() == 0 and 1 <= datetime.now().hour < 10) or (datetime.now().weekday() == 5 and 6 <= datetime.now().hour < 11):
        anomaly_flg = 1
    elif (datetime.now().weekday() == 1 and (2 <= datetime.now().hour < 3 or 9 <= datetime.now().hour < 13)) \
            or (datetime.now().weekday() == 3 and (9 <= datetime.now().hour < 13)) \
            or (datetime.now().weekday() == 4 and (2 <= datetime.now().hour < 3 or 9 <= datetime.now().hour < 13)):
        anomaly_flg = -1
    else:
        anomaly_flg = 0

def fetch_current():
    global sleep_flg
    if over_sleep == 1:
        if (datetime.now().hour == 23 or datetime.now().hour == 3 or datetime.now().hour == 6 or datetime.now().hour == 18) and datetime.now().minute >= 50:
            if sleep_flg == 0:
                sleep_flg = 1
                cancel_allorders()
                priprint('{} sleep mode'.format(datetime.today()))
        elif (datetime.now().hour == 23 or datetime.now().hour == 3 or ((datetime.now().hour == 6 or datetime.now().hour == 18) and over_sleep == 1)) and datetime.now().minute >= 58:
            if mybtc != 0:
                reflesh()
        elif ((datetime.now().hour == 2 or datetime.now().hour == 8 or datetime.now().hour == 20) and datetime.now().minute == 0 and sleep_flg == 1) \
                or (datetime.now().hour == 4 and datetime.now().minute == 15 and sleep_flg == 1):
            sleep_flg = 0
            priprint('{} wake up'.format(datetime.today()))
    else:
        if (datetime.now().hour == 23 or datetime.now().hour == 3) and datetime.now().minute >= 50:
            if sleep_flg == 0:
                sleep_flg = 1
                cancel_allorders()
                priprint('{} sleep mode'.format(datetime.today()))
        elif (datetime.now().hour == 23 or datetime.now().hour == 3) and datetime.now().minute >= 58:
            if mybtc != 0:
                reflesh()
        elif (datetime.now().hour == 0 and datetime.now().minute == 0 and sleep_flg == 1) \
                or (datetime.now().hour == 4 and datetime.now().minute == 15 and sleep_flg == 1):
            sleep_flg = 0
            priprint('{} wake up'.format(datetime.today()))



def fetch_bf():
    global mybtc, entry_price, posside, health
    while True:
        try:
            global position, orders
            position = api.getpositions(product_code='FX_BTC_JPY')
            health = api.gethealth(product_code='FX_BTC_JPY')['status']
            time.sleep(0.6)
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

def param_set():
    global entry_setting, exit_setting, entry_step, sizemin, sizemax, order_count, order_delay, alert_count
    if vr < vr_setting and anomaly_flg == 0:
        entry_setting = settings_inner['entry_setting']
        exit_setting = settings_inner['exit_setting']
        entry_step = settings_inner['entry_step']
        
        order_count = settings_inner['order_count']
        order_delay = settings_inner['order_delay']
        if mybtc == 0:
            alert_count = settings_inner['alert_count']
        if fukuri == 1:
            if mybtc == 0:
                lot_calc(collateral_using, 1)
        else:
            sizemin = settings_inner['sizemin']
            sizemax = settings_inner['sizemax']
    else:
        entry_setting = settings_outer['entry_setting']
        exit_setting = settings_outer['exit_setting']
        entry_step = settings_outer['entry_step']
        
        order_count = settings_outer['order_count']
        order_delay = settings_outer['order_delay']
        if mybtc == 0:
            alert_count = settings_outer['alert_count']
        if fukuri == 1:
            if mybtc == 0:
                lot_calc(collateral_using, order_count)
        else:
            sizemin = settings_outer['sizemin']
            sizemax = settings_outer['sizemax']

def pripara():
    global entry_price, sizealert_count
    msg = ('--------------------------------------------------------------------------------\n'
           ' {} \\{} candle : {} beard top : {} under : {}\n'
           ' [vol] {} [vol_ave] {} [volatility] {} \n'
           ' [range] high-low : {}-{}({}) center : {}\n'
           ' [ently] short:{} long :{}\n'
           ' [exit]  short:{} long :{}\n'
           ' [position] {} {}btc \\{} since {}\n'
           ' [flg] sleep:{} anomaly:{}\n'
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
        str(round(range_center)),
        str(round(ssp)),
        str(round(lsp)),
        str(round(sep)),
        str(round(lep)),
        posside,
        str(mybtc),
        str(entry_price),
        str(poschangetime),
        str(sleep_flg),
        str(anomaly_flg)
    ))
    if mybtc >= sizealert and sizealert_count < sizealert_limit:
        msgList = []
        msgList.append(msg)
        msgList.append('@everyone !alert! position size expand')
        #msgList.append('!alert! position size expand')
        msg = '\n'.join(msgList)
        sizealert_count += 1
    elif mybtc < sizealert:
        sizealert_count = 0
    priprint(msg)

    return


# ローソク足の取得と判定





# 注文処理

def cancel_allorders():
    global buy_status, sell_status, exit_status, obc, osc, obpList, ospList
    while True:
        res = api.cancelallchildorders(product_code='FX_BTC_JPY')
        time.sleep(1)
        if 'error' in str(res):
            print('{} error occurred, retry CANCEL' + str(res).format(datetime.today()))
        else:
            break
    buy_status = dict(side='', id='', size=0, price=9999999)
    sell_status = dict(side='', id='', size=0, price=0)
    exit_status = dict(side='', id='', size=0, price=0, possize=0, pos_price=0)
    obc = 0
    osc = 0
    obpList = dict()
    ospList = dict()
    print('{} all order canceled'.format(datetime.today()))


def order_market(size, buy=True):
    while True:
        if buy:
            side = 'BUY'
        else:
            side = 'SELL'
        res = api.sendchildorder(product_code='FX_BTC_JPY', child_order_type='MARKET', side=side, size=size)
        time.sleep(1)
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
        time.sleep(1)
        if 'acceptance' in str(res):
            print('{} LIMIT {} size:{} price:{} {}'.format(datetime.today(), side, str(size), str(price), str(res)))
            return res['child_order_acceptance_id']
        else:
            order_error_catch(res)
            return ''


def reflesh():
    global ref
    if ref == 0:
        cancel_allorders()
    if mybtc > sizemin + 0.01:
        size = sizemin
    else:
        size = mybtc
    if posside == 'BUY':
        order_market(size, buy=False)
        ref = -1
    elif posside == 'SELL':
        order_market(size, buy=True)
        ref = 1
    time.sleep(1)


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

class Websocketexecutions:
    def __init__(self, product, timescale):
        self.product = product
        self.timescale = str(timescale)+"s"
        self.executions = deque(maxlen=timescale*500)
        self.executionsWebsocket()
        warnings.simplefilter(action="ignore", category=FutureWarning)
    def updatecandle(self):
        tmpExecutions = list(self.executions)
        # datetime生成は勇者ああああ(@AAAAisBraver)さんのnoteのget_exec_datetime関数を参考にさせていただきました。 https://note.mu/17num/n/naba75f04f386
        self.raw = pandas.DataFrame([[dateutil.parser.parse(tick["exec_date"].replace('T',' ')[:-1])+timedelta(hours=9),tick["price"],tick["size"]] for tick in tmpExecutions],columns=["date","price","volume"])
        # ビット鯉(@coibot127)さんのツイートを参考にさせていただいております https://twitter.com/coibot127/status/1025251540125143045
        self.candle=self.raw.set_index('date').resample(self.timescale ,how={"price":"ohlc", "volume":"sum"})
        self.candle.columns=self.candle.columns.droplevel()
        for i in range(len(self.candle)):
            if self.candle["open"][i]!=self.candle["open"][i]:
                self.candle.ix[i,["open","high","low","close"]] =self.candle.ix[i-1,"close"]
    def executionsWebsocket(self):
        def on_message(ws, message):
            messages = json.loads(message)
            recept_data = messages["params"]["message"]
            for i in recept_data:
                self.executions.append(i)
        def on_open(ws):
            ws.send(json.dumps({"method": "subscribe", "params": {"channel": "lightning_executions_{}".format("FX_BTC_JPY")}}))
        def run(ws):
            while True:
                ws.run_forever()
                time.sleep(3)
        ws = websocket.WebSocketApp( "wss://ws.lightstream.bitflyer.com/json-rpc", on_message=on_message )
        ws.on_open = on_open
        websocketThread = threading.Thread(target=run, args=(ws, ))
        websocketThread.start()

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
        global last
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
        self.exit_flg = 0
        self.lastOrderTime = datetime.today()
        err_matilda = 0
        priprint('{} matilda open'.format(datetime.today()))

    def sfd_calc(self, sp, fp):
        sfd = (fp - sp) / sp * 100 if sp != 0 else 0
        return sfd

    def order_buy(self):
        global obc, buy_status, entryvol, obpList
        step = vola * entry_step
        entryvol = bigvol
        if (mybtc <= sizemax- sizemin or posside == 'SELL') and self.lastOrderTime + timedelta(seconds=order_delay)< datetime.today():
            if posside == 'BUY' and (obc == 0 or obc == 1 and buy_status['price'] != entry_price):
                pc = int(mybtc / sizemin) if mybtc >= sizemin else 1
                if pc == 1:
                    buy_status = dict(side='BUY', id='', size=mybtc, price=entry_price)
                else:
                    buy_status = dict(side='BUY', id='', size=mybtc, price=entry_price-(step*(pc+1)/2))
                obpList[obc] = buy_status
                obc = pc
            elif obc == 1 and mybtc == 0:
                if round(lsp) != obpList[0]['price']:
                    if obpList[0]['id'] != '':
                        res = api.cancelchildorder(product_code='FX_BTC_JPY', child_order_acceptance_id=obpList[0]['id'])
                        buy_status = dict(side='', id='', size=0, price=9999999)
                        obc = 0
                        obpList = dict()
                        print('{} buy order canceled'.format(datetime.today(), str(res)))
                        time.sleep(0.6)
            else:
                for i in range(wid):
                    if board['bsize'][i] > entryvol:
                        price = board['bid'][i] + 2
                        if price < buy_status['price'] - step and price < lsp and obc < order_count:
                            id = order_limit(sizemin, price, buy=True)
                            if id != '':
                                buy_status = dict(side='BUY', id=id, size=sizemin, price=price)
                                obpList[obc] = buy_status
                                obc += 1
                                self.lastOrderTime = datetime.today()
                            break
            '''elif obc == 0 and mybtc == 0:
                price = round(lsp)
                id = order_limit(sizemin, price, buy=True)
                if id != '':
                    buy_status = dict(side='BUY', id=id, size=sizemin, price=price)
                    obpList[obc] = buy_status
                    obc += 1
                    self.lastOrderTime = datetime.today()'''

    def order_sell(self):
        global osc, sell_status, entryvol, ospList
        step = vola * entry_step
        entryvol = bigvol
        if (mybtc <= sizemax - sizemin or posside == 'BUY') and self.lastOrderTime + timedelta(seconds=order_delay)< datetime.today():
            if posside == 'SELL' and (osc == 0 or osc == 1 and sell_status['price'] != entry_price):
                pc = int(mybtc / sizemin) if mybtc >= sizemin else 1
                if pc == 1:
                    sell_status = dict(side='SELL', id='', size=mybtc, price=entry_price)
                else:
                    sell_status = dict(side='SELL', id='', size=mybtc, price=entry_price + (step * (pc + 1) / 2))
                ospList[osc] = sell_status
                osc = pc
            elif osc == 1 and mybtc == 0:
                if round(ssp) != ospList[0]['price']:
                    if ospList[0]['id'] != '':
                        res = api.cancelchildorder(product_code='FX_BTC_JPY', child_order_acceptance_id=ospList[0]['id'])
                        sell_status = dict(side='', id='', size=0, price=0)
                        osc = 0
                        ospList = dict()
                        print('{} sell order canceled'.format(datetime.today(), str(res)))
                        time.sleep(0.6)
            else:
                for i in range(wid):
                    if board['asize'][i] > entryvol:
                        price = board['ask'][i] - 2
                        if price > sell_status['price'] + step and price > ssp and osc < order_count:
                            id = order_limit(sizemin, price, buy=False)
                            if id != '':
                                sell_status = dict(side='SELL', id=id, size=sizemin, price=price)
                                ospList[osc] = sell_status
                                osc += 1
                                self.lastOrderTime = datetime.today()
                            break
            '''elif osc == 0 and mybtc == 0:
                price = round(ssp)
                id = order_limit(sizemin, price, buy=False)
                if id != '':
                    sell_status = dict(side='SELL', id=id, size=sizemin, price=price)
                    ospList[osc] = sell_status
                    osc += 1
                    self.lastOrderTime = datetime.today()'''

    def order_exit(self):
        global exit_status, ep
        exit_vola = vola * exit_step * (sizemin / mybtc)
        price = 0
        size = mybtc
        exitvol = bigvol
        if posside == 'SELL':
            side = 'BUY'
            buy = True
            sign = 1
            if anomaly_flg == -1:
                price = entry_price-range_width
            elif self.exit_flg == 1:
                if exit_mode == 2:
                    for i in range(wid):
                        if board['bsize'][i] > exitvol:
                            price = board['bid'][i] + 2
                            if price < entry_price-exit_vola*sign:
                                break
                            else:
                                price = 0
                            break
                elif exit_mode == 1:
                    if sfd_mode == 1:
                        price = lep
                    elif sep > entry_price and mybtc <= settings_inner['sizemax']:
                        price = entry_price-100
                    else:
                        price = sep
            elif self.exit_flg == 2:
                if exit_mode == 0:
                    if sfd_mode == 1:
                        price = lep
                    elif sep > entry_price:
                        price = entry_price-100
                    else:
                        price = sep
                elif sep > entry_price or sfd_mode == 1:
                    price = sep
                else:
                    price = entry_price-100
        elif posside == 'BUY':
            side = 'SELL'
            buy = False
            sign = -1
            if anomaly_flg == 1:
                price = entry_price+range_width
            elif self.exit_flg == 1:
                if exit_mode == 2:
                    for i in range(wid):
                        if board['asize'][i] > exitvol:
                            price = board['ask'][i] - 2
                            if price > entry_price - exit_vola*sign:
                                break
                            else:
                                price = 0
                            break
                elif exit_mode == 1:
                    if lep < entry_price and mybtc <= settings_inner['sizemax']:
                        price = entry_price+100
                    else:
                        price = lep
            elif self.exit_flg == 2:
                if exit_mode == 0:
                    if sfd_mode == -1:
                        price = sep
                    elif lep < entry_price:
                        price = entry_price+100
                    else:
                        price = lep
                elif lep < entry_price or sfd_mode == -1:
                    price = lep
                else:
                    price = entry_price+100

        if price == 0:
            pass
        elif exit_status['id'] != '' and ((exit_status['size'] != size or exit_status['side'] == posside)
                                          or price != exit_status['price']
                                          or exit_status['possize'] != mybtc
                                          or exit_status['pos_price'] != entry_price):
            res = api.cancelchildorder(product_code='FX_BTC_JPY', child_order_acceptance_id=exit_status['id'])
            time.sleep(0.6)
            print('{} exit canceled'.format(datetime.today(), str(res)))
            exit_status = dict(side='', id='', size=0, price=0, possize=0, pos_price=0)
        elif size >= 0.01 and price > 0:
            if exit_status['id'] == '':
                id = order_limit(size, round(price), buy)
                if id != '':
                    exit_status = dict(side=side, id=id, size=size, price=price, possize=mybtc, pos_price=entry_price)
                    print('{} exit submitted'.format(datetime.today()))


    def ently_judge(self):
        global sfd_mode
        sfd = self.sfd_calc(spot_price, last)
        if sleep_flg == 1:
            self.entry_flg = 0
        elif sfd <= -5.2:
            sfd_mode = -1
            self.entry_flg = 0
        elif -5.2 < sfd < -4.8:
            self.entry_flg = 0
            sfd_mode = -1
        elif 4.8 < sfd < 5.2:
            self.entry_flg = 0
            sfd_mode = 1
        elif 5.2 <= sfd:
            sfd_mode = 1
            self.entry_flg = 0
        else:
            sfd_mode = 0
            if range_width < range_setting or range_width > over_range_setting:
                self.entry_flg = 0
                if mybtc == 0 and (obc != 0 or osc != 0):
                    cancel_allorders()
            elif last > range_center and anomaly_flg != 1 and health == ('NORMAL' or 'BUSY'):
                self.entry_flg = -1
            elif last < range_center and anomaly_flg != -1 and health == ('NORMAL' or 'BUSY'):
                self.entry_flg = 1
            else:
                self.entry_flg = 0
                if mybtc == 0 and (obc != 0 or osc != 0):
                    cancel_allorders()


    def exit_judge(self):
        if exit_mode == 0 and anomaly_flg == 0 and sleep_flg == 0:
            self.exit_flg = 0
        elif (posside == 'BUY' and (self.entry_flg == -1 or ref == -1)) or \
                (posside == 'SELL' and (self.entry_flg == 1 or ref == 1)) or \
                (datetime.today() > poschangetime + timedelta(minutes=alert_count * 2) and anomaly_flg == 0):
            self.exit_flg = 3
        elif (((datetime.today() > poschangetime + timedelta(minutes=alert_count)) or sleep_flg == 1) and anomaly_flg == 0)\
                or (posside == 'BUY' and anomaly_flg == -1) or (posside == 'SELL' and anomaly_flg == 1):
            self.exit_flg = 2
        else:
            self.exit_flg = 1



    def run(self):
        global poschangetime, ref, alert_count, lsp, ssp
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
                        self.exit_flg = 0
                        if ref != 0:
                            ref = 0
                            print('{} refleshed'.format(datetime.today()))
                        if fukuri == 1:
                            lot_calc(collateral_using, order_count)
                        continue
                    poschangetime = datetime.today()
                    priprint('{} posside changed {} to {}'.format(poschangetime, possideList[-2], possideList[-1]))
                elif ref != 0 and posside == 'None':
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
                    if mybtc >= 0.01:
                        self.exit_judge()
                        if self.exit_flg == 3:
                            reflesh()
                        elif self.exit_flg >= 1:
                            self.order_exit()
            except Exception as e:
                global err_matilda
                err_matilda = 1
                priprint('@everyone {} matilda error {}'.format(datetime.today(), e.args))
                import traceback
                traceback.print_exc()
                self.stop()
                break
            time.sleep(0.8)

    def stop(self):
        global err_time
        self.stop_event.set()
        #self.thread.join()
        err_time = datetime.today()
        priprint('{} matilda close'.format(datetime.today()))


def main():
    global candle, topbeard, underbeard, candleSign, candlelen, vola, vol_ave, ssp, lsp, sep, lep, \
        range_max, range_min, range_width, range_center, vr
    # --------------------------------------------------
    # 起動メッセージ
    priprint('--------------------------------------------------------------')
    priprint('                      martin start')
    priprint('--------------------------------------------------------------')

    fetch_bf()
    if time_anomaly == 1:
        anomaly_judge()
    cancel_allorders()

    # --------------------------------------------------

    # 初回起動
    fxws = FxWs()
    fxws.run()
    spotws = SpotWs()
    spotws.run()
    websocket = Websocketexecutions("FX_BTC_JPY", foot)
    lastdate = ""

    if fukuri == 1:
        lot_calc(collateral_using, pos_count)
    matilda = Matilda()
    while not websocket.executions:
        time.sleep(1)
    # 以下ループ

    try:
        while True:
            time.sleep(foot)
            websocket.updatecandle()
            lastpos = 0 if lastdate == "" else websocket.candle.index.get_loc(lastdate)
            latestCandle = websocket.candle[lastpos:len(websocket.candle) - 1]
            Time.append(latestCandle.index[-1])
            Open.append(latestCandle['open'][-1])
            High.append(latestCandle['high'][-1])
            Low.append(latestCandle['low'][-1])
            Close.append(latestCandle['close'][-1])
            Vol.append(latestCandle['volume'][-1])
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
            topbeardList.append(topbeard)
            underbeardList.append(underbeard)
            if len(Time) > range_count:
                cl = candlelenList[-vola_count:-1]
                vola = sum(cl) / vola_count
                volaList.append(vola)
                h = High[-range_count:]
                range_max = max(h)
                l = Low[-range_count:]
                range_min = min(l)
                range_width = range_max - range_min
                range_center = round((range_max + range_min) / 2)
                range_centerList.append(range_center)
                vr = range_width / vola
                vrList.append(vr)
                param_set()
                vl = Vol[-vola_count:-1]
                vol_ave = sum(vl) / vola_count
                ssp = range_center + vola * entry_setting
                lsp = range_center - vola * entry_setting
                sep = range_center + vola * exit_setting
                lep = range_center - vola * exit_setting
            if time_anomaly == 1:
                anomaly_judge()
            if err_matilda == 1:
                if datetime.today() > err_time + timedelta(minutes=1):
                    matilda = Matilda()
            #fetch_current()
            pripara()
    except KeyboardInterrupt:
        cancel_allorders()
        matilda.stop()
        sys.exit()
        pass


if __name__ == '__main__':
    main()
