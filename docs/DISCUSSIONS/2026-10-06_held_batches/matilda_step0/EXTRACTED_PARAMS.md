```params matilda_for_TaroCamp37.py
inifile:   # 85 行 = configparser.ConfigParser()
apikey:   # 87 行 = inifile.get('bF_APIKEY', 'apikey')
secret:   # 88 行 = inifile.get('bF_APIKEY', 'secret')
public_api:   # 90 行 = pybitflyer.API()
api:   # 91 行 = pybitflyer.API(api_key=apikey, api_secret=secret)
discord_flg:   # 95 行 = inifile.getint('DISCORD_WEBHOOK', 'flg')
WHURL_a:   # 96 行 = inifile.get('DISCORD_WEBHOOK', 'matilda_alert')
LINE_NOTIFY_API_URL:   # 99 行 = 'https://notify-api.line.me/api/notify'
line_flg:   # 100 行 = inifile.getint('LINE_NOTIFY', 'flgforline')
LINE_NOTIFY_TOKEN:   # 101 行 = inifile.get('LINE_NOTIFY', 'line_token')
sizemin:   # 109 行 = 0.02
sizemax:   # 110 行 = 0.14
sizealert:   # 111 行 = 0.15
sizealert_limit:   # 112 行 = 1
breakexitsize:   # 113 行 = 3
fukuri:   # 115 行 = 1
leverage:   # 116 行 = 4
collateral_using:   # 117 行 = 0.9
pos_count:   # 118 行 = 7
alert_ratio:   # 119 行 = 7
foot:   # 123 行 = 1
vola_count:   # 124 行 = 40
range_count:   # 125 行 = 40
alert_count:   # 126 行 = 20
range_setting:   # 134 行 = 150
over_range_setting:   # 135 行 = 100000
entry_setting:   # 141 行 = 2
exit_setting:   # 142 行 = 0.8
break_delay:   # 144 行 = 1
beard_ignore:   # 151 行 = 1
step_setting:   # 156 行 = 1
step_exit:   # 157 行 = 0.8
bigvol:   # 160 行 = 0.1
wid:   # 161 行 = 100
entryvol:   # 163 行 = bigvol
```
```params matilda_v52.py
inifile:   # 100 行 = configparser.ConfigParser()
apikey:   # 102 行 = inifile.get('bF_APIKEY', 'apikey')
secret:   # 103 行 = inifile.get('bF_APIKEY', 'secret')
public_api:   # 105 行 = pybitflyer.API()
api:   # 106 行 = pybitflyer.API(api_key=apikey, api_secret=secret)
discord_flg:   # 110 行 = inifile.getint('DISCORD_WEBHOOK', 'flg')
WHURL_a:   # 111 行 = inifile.get('DISCORD_WEBHOOK', 'matilda_alert')
LINE_NOTIFY_API_URL:   # 114 行 = 'https://notify-api.line.me/api/notify'
line_flg:   # 115 行 = inifile.getint('LINE_NOTIFY', 'flgforline')
LINE_NOTIFY_TOKEN:   # 116 行 = inifile.get('LINE_NOTIFY', 'line_token')
settings_inner:   # 128 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_inner.entry_setting:   # 128 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_inner.exit_setting:   # 128 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_inner.entry_step:   # 128 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_inner.sizemin:   # 128 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_inner.sizemax:   # 128 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_inner.order_count:   # 128 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_inner.order_delay:   # 128 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_inner.alert_count:   # 128 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
vr_setting:   # 129 行 = 100
settings_outer:   # 130 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_outer.entry_setting:   # 130 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_outer.exit_setting:   # 130 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_outer.entry_step:   # 130 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_outer.sizemin:   # 130 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_outer.sizemax:   # 130 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_outer.order_count:   # 130 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_outer.order_delay:   # 130 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
settings_outer.alert_count:   # 130 行 = dict(entry_setting=2, exit_setting=2, entry_step=2, sizemin=0.01, sizemax=0.04, order_count=4, order_delay=1, alert_count=1)
time_anomaly:   # 132 行 = 0
over_sleep:   # 133 行 = 0
order_delay:   # 134 行 = settings_outer['order_delay']
entry_setting:   # 136 行 = settings_outer['entry_setting']
exit_setting:   # 137 行 = settings_outer['exit_setting']
entry_step:   # 138 行 = settings_outer['entry_step']
sizemin:   # 140 行 = settings_outer['sizemin']
sizemax:   # 141 行 = settings_outer['sizemax']
order_count:   # 142 行 = settings_outer['order_count']
sizealert:   # 144 行 = 0.4
sizealert_limit:   # 145 行 = 1
foot:   # 149 行 = 5
vola_count:   # 150 行 = 6
range_count:   # 151 行 = 6
alert_count:   # 152 行 = 1
range_setting:   # 158 行 = 100
over_range_setting:   # 159 行 = 900000
exit_mode:   # 162 行 = 1
exit_step:   # 163 行 = 0
beard_ignore:   # 166 行 = 1
bigvol:   # 170 行 = 1
wid:   # 171 行 = 200
fukuri:   # 174 行 = 0
leverage:   # 175 行 = 4
collateral_using:   # 176 行 = 0.95
pos_count:   # 177 行 = 5
alert_ratio:   # 178 行 = 10
```
