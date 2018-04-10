# encoding: UTF-8

"""
一个ATR-RSI指标结合的交易策略，适合用在股指的1分钟和5分钟线上。

注意事项：
1. 作者不对交易盈利做任何保证，策略代码仅供参考
2. 本策略需要用到talib，没有安装的用户请先参考www.vnpy.org上的教程安装
3. 将IF0000_1min.csv用ctaHistoryData.py导入MongoDB后，直接运行本文件即可回测策略

"""

import talib
import numpy as np

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate


########################################################################
class TurtleStrategy(CtaTemplate):
    """海龟交易策略"""
    className = 'TurtleStrategy'
    author = u'用Python的交易员'

    # 策略参数
    atrLength = 10          # 计算ATR指标的窗口数
    initDays = 20           # 初始化数据所用的天数

    # 策略变量
    bar = None                  # K线对象
    barMinute = EMPTY_STRING    # K线当前的分钟

    bufferSize = 20                    # 需要缓存的数据的大小
    bufferCount = 0                     # 目前已经缓存了的数据的计数
    highArray = np.zeros(bufferSize)    # K线最高价的数组
    lowArray = np.zeros(bufferSize)     # K线最低价的数组
    closeArray = np.zeros(bufferSize)   # K线收盘价的数组
    
    atrCount = 0                        # 目前已经缓存了的ATR的计数
    atrArray = np.zeros(bufferSize)     # ATR指标的数组
    atrValue = 0                        # 最新的ATR指标数值

    orderList = []                      # 保存委托代码的列表

    last_buy_prcie = 0  #上一次买入价
    hold_flag = False   # 是否持有头寸标志
    limit_unit = 4     # 限制最多买入的单元数
    unit = 0       # 现在买入1单元的股数
    add_time = 0

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'atrLength']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'atrValue']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(TurtleStrategy, self).__init__(ctaEngine, setting)
        
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）        

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
    
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            # print "bar", bar.__dict__
            self.onBar(bar)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 计算K线
        tickMinute = tick.datetime.minute
        # print "tick",tick.__dict__

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
            bar.datetime = tick.datetime    # K线的时间设为第一个Tick的时间

            self.bar = bar                  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute     # 更新当前的分钟
        else:                               # 否则继续累加新的K线
            bar = self.bar                  # 写法同样为了加快速度

            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        for orderID in self.orderList:
            self.cancelOrder(orderID)
        self.orderList = []

        # 保存K线数据
        self.closeArray[0:self.bufferSize-1] = self.closeArray[1:self.bufferSize]
        self.highArray[0:self.bufferSize-1] = self.highArray[1:self.bufferSize]
        self.lowArray[0:self.bufferSize-1] = self.lowArray[1:self.bufferSize]
        
        self.closeArray[-1] = bar.close
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low


        self.bufferCount += 1

        print "self.bufferCount",self.bufferCount,"self.bufferSize",self.bufferSize
        # print "self.lowArray",len(self.lowArray)
        if self.bufferCount <= self.bufferSize:
            # 若bar数量未达到初始化所需数量，则继续积累
            return

        # 计算ATR指标数值

        self.atrValue = talib.ATR(self.highArray,
                                  self.lowArray, 
                                  self.closeArray,
                                  self.atrLength)[-1]
        # print "self.atrValue",self.atrValue

        # 计算唐奇安通道
        # print "self.highArray",self.highArray
        # print "self.highArray[0:-1]",self.highArray[0:-1]
        self.up = max(self.highArray[0:-1])
        self.down = min(self.lowArray[0:-1])


        # 计算买卖单位
#####缺少账户查询
        # self.unit = 0.01*Account/self.atrValue  # 单位：股
        self.unit = 100
        # 判断是否要进行交易

        print "bar.date",bar.date
        print "bar.high",bar.high,"bar.low",bar.low,"bar.close",bar.close
        print "self.atrValue",self.atrValue
        print "self.up",self.up,"self.down",self.down
        print "self.pos",self.pos


        if self.pos == 0:  # 当前无仓位
            if bar.close > self.up:  # 若股价突破上轨
                print u"多头建仓", bar.close
                orderID = self.buy(bar.close + 5, self.unit)  # 这里为了保证成交，选择超价5个整指数点下单
                self.orderList.append(orderID)
#####缺少已成交检验
                self.add_time += 1
                self.last_price = bar.close  # 此处记录当前bar的close价作为下次买入的参考基准价
            elif bar.close < self.down:  # 若股价突破下轨
                print u"空头建仓", bar.close
                orderID = self.short(bar.close - 5, self.unit)  # 这里为了保证成交，选择超价5个整指数点下单
                self.orderList.append(orderID)
#####缺少已成交检验
                self.add_time += 1
                self.last_price = bar.close  # 此处记录当前bar的close价作为下次买入的参考基准价
        elif self.pos > 0:  # 持有多头仓位

            if self.add_time >= self.limit_unit:  # 若已达到仓位限制
                pass
            else:
                if bar.close > self.last_price + 0.5 * self.atrValue:  # 若股价在上一次买入（或加仓）的基础上上涨了0.5N，则加仓一个Unit。
                    print u"多头追仓", bar.close
                    orderID = self.buy(bar.close + 5, self.unit)
                    self.orderList.append(orderID)
                    self.last_price = bar.close
#####缺少已成交检验
                    self.add_time += 1

            if bar.close < self.last_price - 2 * self.atrValue:  # 当价格比最后一次买入价格下跌2N时，则卖出全部头寸止损。
                orderID = self.sell(bar.close, abs(self.pos), stop=True)
                self.orderList.append(orderID)
                print u"多头止损", bar.close
#####缺少已成交检验
                self.add_time = 0

            if bar.close < self.down:  # 当股价跌破下轨，清空头寸结束本次交易
                orderID = self.sell(bar.close, abs(self.pos), stop=True)
                self.orderList.append(orderID)
                print u"多头清仓", bar.close
            self.add_time = 0
        elif self.pos < 0:  # 持有空头仓位

            if self.add_time >= self.limit_unit:  # 若已达到仓位限制
                pass
            else:
                if bar.close < self.last_price - 0.5 * self.atrValue:  # 若股价在上一次买入（或加仓）的基础上又下跌了0.5N，则加仓一个Unit。
                    print u"空头追仓", bar.close
                    orderID = self.short(bar.close - 5, self.unit)
                    self.orderList.append(orderID)
                    self.last_price = bar.close
                    #####缺少已成交检验
                    self.add_time += 1

            if bar.close > self.last_price + 2 * self.atrValue:  # 当价格比最后一次买入价格上涨2N时，则卖出全部空头头寸止损。
                orderID = self.cover(bar.close, abs(self.pos), stop=True)
                self.orderList.append(orderID)
                print u"空头止损", bar.close
                #####缺少已成交检验
                self.add_time = 0

            if bar.close > self.up:  # 当股价突破上轨，清空空头头寸结束本次交易
                orderID= self.cover(bar.close, abs(self.pos), stop=True)
                self.orderList.append(orderID)
                print u"空头清仓", bar.close
            self.add_time = 0
        print "#############################"
        # # 持有多头仓位
        # elif self.pos > 0:
        #     # 计算多头持有期内的最高价，以及重置最低价
        #     self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
        #     self.intraTradeLow = bar.low
        #     # 计算多头移动止损
        #     longStop = self.intraTradeHigh * (1-self.trailingPercent/100)
        #     # 发出本地止损委托，并且把委托号记录下来，用于后续撤单
        #     orderID = self.sell(longStop, abs(self.pos), stop=True)
        #     self.orderList.append(orderID)
        # # 持有多头仓位
        # elif self.pos > 0:
        #     # 计算多头持有期内的最高价，以及重置最低价
        #     self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
        #     self.intraTradeLow = bar.low
        #     # 计算多头移动止损
        #     longStop = self.intraTradeHigh * (1-self.trailingPercent/100)
        #     # 发出本地止损委托，并且把委托号记录下来，用于后续撤单
        #     orderID = self.sell(longStop, abs(self.pos), stop=True)
        #     self.orderList.append(orderID)

        # # 持有空头仓位
        # elif self.pos < 0:
        #     self.intraTradeLow = min(self.intraTradeLow, bar.low)
        #     self.intraTradeHigh = bar.high
        #
        #     shortStop = self.intraTradeLow * (1+self.trailingPercent/100)
        #     orderID = self.cover(shortStop, abs(self.pos), stop=True)
        #     self.orderList.append(orderID)

        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()

if __name__ == '__main__':
    # 提供直接双击回测的功能
    # 导入PyQt4的包是为了保证matplotlib使用PyQt4而不是PySide，防止初始化出错
    from vnpy.trader.app.ctaStrategy.ctaBacktesting import *
    from PyQt4 import QtCore, QtGui
    
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20120101')
    
    # 设置产品相关参数
    engine.setSlippage(0.2)     # 股指1跳
    engine.setRate(0.3/10000)   # 万0.3
    engine.setSize(300)         # 股指合约大小 
    engine.setPriceTick(0.2)    # 股指最小价格变动
    
    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, 'IF0000')
    
    # 在引擎中创建策略对象
    d = {'atrLength': 11}
    engine.initStrategy(AtrRsiStrategy, d)
    
    # 开始跑回测
    engine.runBacktesting()
    
    # 显示回测结果
    engine.showBacktestingResult()
    
    ## 跑优化
    #setting = OptimizationSetting()                 # 新建一个优化任务设置对象
    #setting.setOptimizeTarget('capital')            # 设置优化排序的目标是策略净盈利
    #setting.addParameter('atrLength', 12, 20, 2)    # 增加第一个优化参数atrLength，起始11，结束12，步进1
    #setting.addParameter('atrMa', 20, 30, 5)        # 增加第二个优化参数atrMa，起始20，结束30，步进1
    #setting.addParameter('rsiLength', 5)            # 增加一个固定数值的参数
    
    ## 性能测试环境：I7-3770，主频3.4G, 8核心，内存16G，Windows 7 专业版
    ## 测试时还跑着一堆其他的程序，性能仅供参考
    #import time    
    #start = time.time()
    
    ## 运行单进程优化函数，自动输出结果，耗时：359秒
    #engine.runOptimization(AtrRsiStrategy, setting)            
    
    ## 多进程优化，耗时：89秒
    ##engine.runParallelOptimization(AtrRsiStrategy, setting)     
    
    #print u'耗时：%s' %(time.time()-start)