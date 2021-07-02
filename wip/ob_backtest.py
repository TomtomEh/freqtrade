from freezegun import freeze_time

from OBOnlyWS import OBOnlyWS
from OBOnlyWSv2 import OBOnlyWSv2
from OBOnlyWSnext import OBOnlyWSnext
from datetime import datetime,timedelta,timezone
import os
from threading import Lock
import time
import pytz
tz=pytz.timezone( 'Europe/Paris')

from freqtrade.persistence import LocalTrade,Order
date_time_str = '03/07/21 00:00+02:00'
#date_time_str = '29/06/21 00:00+02:00'

#date_time_str = '26/06/21 20:50+02:00'
date_time_obj = datetime.strptime(date_time_str, '%d/%m/%y %H:%M%z')

end=int(date_time_obj.timestamp())
date_time_str = '30/06/21 16:00+02:00'
# date_time_str = '28/06/21 02:00+02:00'

date_time_obj = datetime.strptime(date_time_str, '%d/%m/%y %H:%M%z')

start=int(date_time_obj.timestamp())

from os import listdir
from os.path import isfile, join
import numpy as np
mypath="/home/khadas/dev/freqtrade_unstable/depth/ADA/"
files = [int(os.path.splitext(f)[0]) for f in listdir(mypath) if isfile(join(mypath, f))]
files=np.array(files)
ds=files[files>start]
ds=ds[ds<end]

ds=np.sort(ds)
conf={
        "dry_run":True,
        "stake_currency":"BUSD",
        "exchange": {
            "name": "binance",
            "key": "qsdfqsd",
            "secret": "qsdfqsdf",
            "ccxt_config": {"enableRateLimit": True},
            "ccxt_async_config": {
                "enableRateLimit": True,
                "rateLimit": 1000
            },
            "pair_whitelist":[],
            "pair_blacklist":[],
        }
    }
class Wallets:
    def get_trade_stake_amount(self,pair):
        return 100    
class bt_DepthCache:
    bids=None
    asks=None
    symbol="ADAUSDT"
    def get_bids(self):
        return self.bids
    def get_asks(self):
        return self.asks    
           
class MyFT:
    trades=[]
    _open_trades=[]
    wallets=Wallets()
    _sell_lock=Lock()
    #wallets=MyWallet()
    def open_trades(self,pair):
        if pair:
            for trade in self._open_trades :
                return trade
            return None    
        return self._open_trades 
    closed_kline=False           
    def execute_buy(self,pair,stake_amount,price):
        if len(self._open_trades) >0:
            return
        print(datetime.now().timestamp())
        print("buy")
        trade=LocalTrade()
        o=Order()
        o.status="open"
        o.side="buy"
        o.order_date=datetime.now()

        trade.orders.append(o)
        trade.pair=pair
        trade.open_rate=price
        trade.open_date=datetime.now()
        self._open_trades.append(trade)
        self.closed_kline=False
    

    def execute_sell(self,trade,price,reason):
        #print("sell")

        trade.close_rate=price
        o=Order()
        o.status="open"
        o.side="sell"
        o.order_date=datetime.now()
        trade.sell_reason=reason
        self.closed_kline=False

        trade.orders.append(o)
    gain=[]
    last_data= None
    def check_price(self,dc,msg):
        for t in self._open_trades:
            for o in t.orders:
                #print(o.status)
                if o.status == "open":
                    if o.order_date < datetime.now() -timedelta(minutes=2):
                        if o.side =="buy":
                            t=self._open_trades.pop()
                            t.orders.clear() 
                        o.status="canceled"
                        #print("canceled")
                        return    
                    if o.side =="buy":
                        best_price=float(msg["k"]["c"]) 
                        if self.closed_kline:
                            best_price=float(msg["k"]["l"])
                        if t.open_rate>= dc.asks[0][0] or t.open_rate>= best_price:
                            
                            o.status="closed"
                    if o.side =="sell":
                        best_price=float(msg["k"]["c"]) 
                        if self.closed_kline:
                            best_price=float(msg["k"]["h"])
                        if t.close_rate <= dc.bids[0][0] or t.open_rate <=  float(msg["k"]["c"]):
                           
                            #f=open("trades2.csv", "a+")
                            gain=(t.close_rate-t.open_rate)/t.open_rate
                            print(f"{t.open_date.astimezone(tz)} {datetime.now().astimezone(tz)}, {t.pair}, {t.open_rate}, {t.close_rate}, {gain} {t.sell_reason.sell_type}\n")
                            #f.close()
                            self.gain.append(gain)
                            gain=np.array(ft.gain)

                            print(np.sum(gain))     
                            t=self._open_trades.pop()
                            
                            t.orders.clear()
                            self.trades.append(t)
                            o.status="closed"
                    if msg["k"]["x"]:
                        self.closed_kline=True
    def get_trades(self):
        res = []
        for key in self.trades:
            res.append(self.trades[key])
        return res
with freeze_time(date_time_obj) as frozen_datetime:
    frozen_datetime.move_to(date_time_obj)

    ft=MyFT()
    strat=OBOnlyWS(conf)
    strat.ft=ft
    strat.backtesting=True
    prev=None
    i=0
    dc=bt_DepthCache()

    for ob in ds:
        arr=np.load(f"{mypath}{ob}.npz")
        #print(f"ib {ob}")
        frozen_datetime.move_to(datetime.fromtimestamp(ob,tz=timezone.utc))
        dc.bids=arr["bids"]
        dc.asks=arr["asks"]
        ohlcv=arr["ohlcv"]
        if ohlcv[4] == '0':
            continue
        if prev is  None :
            prev=ohlcv
        x=True
        if np.array_equal(ohlcv[:5],prev[:5]):
            x=False
        
        msg={"s":"ADAUSDT",
            "k":{
                "o":ohlcv[5],
                "h":ohlcv[6],
                "l":ohlcv[7],
                "c":ohlcv[8],
                "v":ohlcv[9],
                "V":ohlcv[9],

                "x":x  
            }   
        
        
        }

        strat.handle_socket_message(msg)
        strat.handle_dcm_message(dc)
        ft.check_price(dc,msg)
        #print(msg)
        prev=ohlcv
        #i+=1
        #if i >200:
        #    break
gain=np.array(ft.gain)
print(gain)
print(np.sum(gain))        
    #instantiate strat

    #compute start date
    #read file names
    #convert filenames to int
