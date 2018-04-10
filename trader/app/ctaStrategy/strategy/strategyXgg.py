# encoding: UTF-8

"""
这里的Demo是一个最简单的策略实现，并未考虑太多实盘中的交易细节，如：
1. 委托价格超出涨跌停价导致的委托失败
2. 委托未成交，需要撤单后重新委托
3. 断网后恢复交易状态
4. 等等
这些点是作者选择特意忽略不去实现，因此想实盘的朋友请自己多多研究CTA交易的一些细节，
做到了然于胸后再去交易，对自己的money和时间负责。
也希望社区能做出一个解决了以上潜在风险的Demo出来。
"""

from __future__ import division

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING, EMPTY_FLOAT
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate

import numpy as np


########################################################################
class XggStrategy(CtaTemplate):
    """双指数均线策略Demo"""
    className = 'XggStrategy'
    author = u'用Demo的交易员'

    # 策略参数
    initDays = 35  # 初始化数据所用的天数
    StdDevUp = 2  # 计算上下轨所用的参数
    Scale = 1.2


    # 策略变量
    bar = None
    barMinute = EMPTY_STRING

    AveMa = []  # 快速EMA均线数组
    AveMa0 = EMPTY_FLOAT  # 当前最新的快速EMA
    AveMa1 = EMPTY_FLOAT  # 上一根的快速EMA


    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 "StdDevUp"]

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'AveMa0',
               'AveMa1']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(XggStrategy, self).__init__(ctaEngine, setting)

        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）
        self.AveMa = []
        self.Close = []
        self.StdValue = 0
        self.UpperBand = []
        self.LowerBand = []

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略初始化...')

        initData = self.loadBar(self.initDays)
        # type(initData)为 list
        for bar in initData:
            self.onBar(bar)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略启动')
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略停止')
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 计算K线
        tickMinute = tick.datetime.minute
        # print "tick",tick.__dict__
        print "+" * 10, "get tick data"
        print "tickMinute", tickMinute
        print "tick.datetime.minute", self.barMinute
        if tickMinute != self.barMinute:
            if self.bar:
                self.onBar(self.bar)

            bar = VtBarData()
            bar.vtSymbol = tick.vtSymbol
            bar.symbol = tick.symbol
            bar.exchange = tick.exchange

            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice

            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime  # K线的时间设为第一个Tick的时间

            # 实盘中用不到的数据可以选择不算，从而加快速度
            # bar.volume = tick.volume
            # bar.openInterest = tick.openInterest

            self.bar = bar  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute  # 更新当前的分钟
            # print "-"*20
            # print "tickMinute != self.barMinute"
            # print bar.__dict__

        else:  # 否则继续累加新的K线
            bar = self.bar  # 写法同样为了加快速度

            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice


    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        bar.close = float(bar.close)

        self.Close.append(bar.close)

        if len(self.Close) < self.initDays:
            if not self.AveMa0:
                self.AveMa0 = bar.close
                self.AveMa.append(self.AveMa0)
            else:
                self.AveMa1 = self.AveMa0
                self.AveMa0 = bar.close
                self.AveMa.append(self.AveMa0)
        else:
            self.AveMa0 = np.mean(np.array(self.Close[-self.initDays:]))
            self.AveMa.append(self.AveMa0)
            self.StdValue = np.std(np.array(self.Close[-self.initDays:])).item()

        # print "self.Close", self.Close
        # print "self.AveMa", self.AveMa


        UpperBand0 = self.AveMa0 + self.StdDevUp * self.StdValue
        LowerBand0 = self.AveMa0 - self.StdDevUp * self.StdValue
        self.UpperBand.append(round(UpperBand0))
        self.LowerBand.append(round(LowerBand0))
        # 判断买卖


        if len(self.Close) >1:

            crossOver = self.Close[-2] > self.UpperBand[-2] and self.Close[-1] < self.UpperBand[-1]  # 金叉上穿
            crossBelow = self.Close[-2] < self.LowerBand[-2] and self.Close[-1] > self.LowerBand[-1]  # 死叉下穿

            if self.pos >= 1 and crossOver:
                self.buy(bar.close, 1)
            elif self.pos >=0 and crossBelow:
                self.short(bar.close, 1)
            elif self.pos > 0 and bar.close < self.AveMa0:
                self.sell(bar.close, 1)
            elif self.pos < 0 and bar.close > self.AveMa0:
                self.cover(bar.close, 1)

        print "self.Close",self.Close
        print "self.UpperBand",self.UpperBand
        print "self.LowerBand",self.LowerBand
        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
