# coding: utf-8

import urllib2
import string

symbol = "RB0"
db_symbol = str.lower(symbol)
base_url = "http://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesDailyKLine?symbol="

url = base_url + symbol
raw_data = urllib2.urlopen(url).read()
raw_data_object = open(db_symbol+"_raw_daily.txt", "w")
print raw_data
raw_data_object.write(raw_data)
raw_data_object.close()


import json
import pymongo
from datetime import datetime


DAILY_DB_NAME  = "VnTrader_Daily_Db"
raw_data = open(db_symbol+"_raw_daily.txt", "r")
raw_daily_data = raw_data.read()
raw_data.close()
data = json.loads(raw_daily_data)

def check_data(data):
    for key,daily in enumerate(data):
        daily[1] = float(daily[1])
        daily[2] = float(daily[2])
        daily[3] = float(daily[3])
        daily[4] = float(daily[4])
        daily[5] = float(daily[5])
        if not daily[5]:
            print data.pop(key)


check_data(data)


class VtBarData(object):
    """K线数据"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtBarData, self).__init__()

        self.vtSymbol = ""  # vt系统代码
        self.symbol = ""  # 代码
        self.exchange = ""  # 交易所

        self.open = ""  # OHLC
        self.high = ""
        self.low = ""
        self.close = ""

        self.date = ""  # bar开始的时间，日期
        self.time = ""  # 时间
        self.datetime = None  # python的datetime时间对象

        self.volume = ""  # 成交量
        self.openInterest = ""  # 持仓量


print u'开始写入%s日行情' % db_symbol
globalSetting = {"mongoHost": "localhost","mongoPort": 27017}
# 查询数据库中已有数据的最后日期
dbClient = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
cl = dbClient[DAILY_DB_NAME][db_symbol]
cx = cl.find(sort=[('datetime', pymongo.DESCENDING)])
if cx.count():
    last = cx[0]
else:
    last = ''

if data:
    # 创建datetime索引
    dbClient[DAILY_DB_NAME][db_symbol].ensure_index([('datetime', pymongo.ASCENDING)],
                                                      unique=True)

    for d in data:
        bar = VtBarData()
        bar.vtSymbol = db_symbol
        bar.symbol = db_symbol
        try:
            bar.exchange = ""

            bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume = tuple(d)

            bar.time = ""
            bar.datetime = datetime.strptime(bar.date.replace('-', ''), '%Y%m%d')
            bar.openInterest = 0
        except KeyError:
            print d

        flt = {'datetime': bar.datetime}
        dbClient[DAILY_DB_NAME][db_symbol].update_one(flt, {'$set': bar.__dict__}, upsert=True)

    print u'%s下载完成' % db_symbol
else:
    print u'找不到合约%s' % db_symbol






# from WindPy import w
# symbol = "000001.SZ"
# "open,high,low,close,volume,amt"
# from_date = "2015-11-22"
# to_date = "2015-12-22"
#
# w.start()
# # daily_ohlc = w.wsd(symbol, "open,high,low,close,volume,amt", from_date, to_date, "Fill=Previous")
# # print daily_ohlc
# print w.wsd("RB1710.SHF", "open,high,low,close,volume,amt", "2016-12-01", "2017-07-24", "PriceAdj=F")

