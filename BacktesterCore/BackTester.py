#AUTHOR: TrippyBruh#
import talib, random, statistics, numpy
from progressbar import ProgressBar
from typing import List, Final
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from .BackTesterHelpers import *

#BASIC 
class BacktestCandle():
    indicatorsNames = ["OHLC/4", "RSI(14)", "RSI(42)", "BB_HIGHER", "BB_LOWER", "MACD(12, 26, 9)", "AROON_OSC", "OTHERS"]
    SMAs_periods = [8, 20, 50, 100, 200, 400]
    EMAs_periods = [8, 20, 50, 100, 200, 400]

    def __init__(self, timestamp = int, open = float, high = float, low = float, close = float, **kwargs):
        if open < close:
            self.bullish = True
        else: self.bullish = False
        self.timestamp = timestamp
        self.open = open
        self.close = close
        self.high = high
        self.low = low
        self.isHeiken = kwargs.get('isHeiken')
        if not self.isHeiken:
            self.indicators = {}.fromkeys(self.indicatorsNames, 0.0)
            self.SMAs = {}.fromkeys(self.SMAs_periods, 0.0)
            self.EMAs = {}.fromkeys(self.EMAs_periods, 0.0)
            self.indicators.update({ "OHLC/4" : (open+high+low+close)/4})

    def getPercentageChange(self):
        try:
            if not self.bullish:
                return ((self.close/self.open)-1)*100 #decremento
            else: return ((self.open/self.close)-1)*-100 #incremento
        except ZeroDivisionError:
            return float('inf')
    
    def getHeikenAshi(self, previousCandle):
        return BacktestHeikenCandle(previousCandle.timestamp, (previousCandle.open + previousCandle.close)/2, max(self.high, self.open, self.close), 
               min(self.low, self.open, self.close), (self.open + self.high + self.low + self.close)/4, isHeiken = True)

    def getAllIndicators(self):
        return list(self.indicators.values())

    def getAllSMAs(self):
        return list(self.SMAs.values())
    
    def getAllEMAs(self):
        return list(self.EMAs.values())

    def addValueRSI14(self, value):
        self.indicators.update({"RSI(14)" : value})

    def addValueRSI42(self, value):
        self.indicators.update({"RSI(42)" : value})
    
    def addValueEMA(self, period, value):
        self.EMAs.update({period : value})

    def addValueSMA(self, period, value):
        self.SMAs.update({period : value})

    def __str__(self):
        if self.isHeiken:
            str = f"OPEN: {self.open} $ ---[HIGH: {self.high}, LOW: {self.low}]---> CLOSE: {self.close} $ = {numpy.round(self.getPercentageChange(), 4)} % ({timestampToDate(self.timestamp)})\n"
        else: str = f"OPEN: {self.open} $ ---> CLOSE: {self.close} $ = {numpy.round(self.getPercentageChange(), 4)} % ({timestampToDate(self.timestamp)})\nIndicators: {self.indicatorsNames}\nEMAS: {self.EMAs}\nSMAS: {self.SMAs}\n"
        return str

class BacktestHeikenCandle(BacktestCandle):

    def __init__(self, timestamp=int, open=float, high=float, low=float, close=float, **kwargs):
        super().__init__(timestamp, open, high, low, close, **kwargs)

    def strongUptrend(self):
        return self.low >= self.open

    def strongDowntrend(self):
        return self.high <= self.open

class BacktestTrade():

    def __init__(self, timestampEntry = int, isBuy = bool, entryPrice = float, qty = float):
        self.ID = id(self)
        self.timestampEntry = timestampEntry
        self.timestampExit = 0
        self.isBuy = isBuy
        self.entryPrice = entryPrice
        self.qty = qty
        self.qtyUSD = entryPrice*qty
        self.exitPrice = 0
        self.rawPNL = 0
        self.pnlQTY = 0
        self.pnlUSD = 0
    
    def isClosed(self):
        return self.exitPrice != 0 and self.timestampExit != 0

    def getAgeInCandles(self, currentTimestamp = int, timeframe = str):
        return (currentTimestamp-self.timestampEntry)/BacktestDataset().timeframes.get(timeframe)

    def getPNL(self, currentPrice):
        if self.isBuy:
            return ((currentPrice/self.entryPrice)-1)*100
        else: return ((self.entryPrice/currentPrice)-1)*100

    def closeTrade(self, closingPrice = float, timestampExit = int):
        if not self.isClosed():
            self.exitPrice = closingPrice
            self.timestampExit = timestampExit
            self.rawPNL = self.getPNL(closingPrice)
            if self.isBuy:
                self.pnlUSD = (self.rawPNL/100)*self.qtyUSD
                self.pnlQTY = self.pnlUSD/closingPrice
            else: 
                self.pnlQTY = (self.rawPNL/100)*self.qty
                self.pnlUSD = self.pnlQTY*closingPrice

    def __str__(self):
        if self.isBuy:
            side = "LONG"
            order1 = "BUY"
            order2 = "SELL"
        else: 
            side = "SHORT"
            order1 = "SELL"
            order2 = "BUY"
        if self.timestampEntry < self.timestampExit and self.exitPrice > 0:
            return f"{side} trade - ({timestampToDate(self.timestampEntry)}) [Opened: {order1} at {self.entryPrice} $ ---({std_2rounding(self.rawPNL)} %)---> Closed: {order2} at {self.exitPrice} $] ({timestampToDate(self.timestampExit)})"
        else: return f"{side} trade - ({timestampToDate(self.timestampEntry)}) [Opened: {order1} at {self.entryPrice} $ ---> Trade still open]\n"

class BacktestLeveragedTrade(BacktestTrade):

    #default isolated margin
    stdLiqFactor = 0.85

    def __init__(self, timestampEntry=int, isBuy=bool, entryPrice=float, qty=float, leverage = float):

        def setLiquidationPrice():
            totalLiqDiff = entryPrice/leverage
            if isBuy:
                return entryPrice - (totalLiqDiff*self.stdLiqFactor)
            else: return entryPrice + (totalLiqDiff*self.stdLiqFactor)

        if leverage > 1:
            super().__init__(timestampEntry, isBuy, entryPrice, qty)
            self.leverage = leverage
            self.liqPrice = setLiquidationPrice()
        else: raise AttributeError("Levarege must be greater than 1")

    def checkLiquidation(self, timestamp, currentPrice):

        def liquidate():
            self.timestampExit = timestamp
            self.exitPrice = self.liqPrice
            self.rawPNL = -100.0
            self.pnlUSD = -self.qtyUSD
            self.pnlQTY = -self.qty
    
        if (self.isBuy and currentPrice <= self.liqPrice) or (not self.isBuy and currentPrice >= self.liqPrice):
            liquidate()
            return True
        else: return False
    
    def getPNL(self, currentPrice):
        return super().getPNL(currentPrice)*self.leverage
    
    def __str__(self):
        return super().__str__() + f"\nLeverage: {self.leverage}X, Liquidation price: {std_4rounding(self.liqPrice)} $"

#LOADING AND RUNNING   
class BackTestLoader():

    def __init__(self):
        self.dataset = BacktestDataset()
        self.startingYear = 0
        self.endingYears = 0
        self.ready = False
    
    def checkReady(self):
        if self.dataset.checkLoadedDatesOrder():
            self.ready = True
        else: 
            self.dataset.dumpLoadedCandles()
            raise RuntimeError("Error in candles timestamps!")

    def loadYearlyBacktest(self, timeframe, market, startingYear, extraYears):
        if startingYear > 2009:
            if extraYears >= 1:
                for x in range(extraYears+1):
                    self.dataset.loadCandlesFromFile(candlesDataFilepath(timeframe, market, f"{startingYear + x}"))
            else: self.dataset.loadCandlesFromFile(candlesDataFilepath(timeframe, market, f"{startingYear}"))
        else: raise AttributeError(f"{startingYear} is too small!")

        self.startingYear = startingYear
        self.endingYear = startingYear + extraYears
        self.checkReady()
    
    def loadMonthlyBacktest(self):
        pass

class BacktestTrendStrategy():

    MIN_ACT_SCORE = 10
    MAX_ACT_SCORE = 40
    RARE_RESET_FACTOR = 5
    NORMAL_RESET_FACTOR = 25 
    FREQUENT_RESET_FACTOR = 100

    def __init__(self):
        self.bullBias = {}
        self.bearBias = {}
        self.heikenBias = {}
        self.bull = 0
        self.bear = 0

    def preloadTrendStrategy(self, datasetCandles = list[BacktestCandle]):
        resetFactor = int(len(datasetCandles)/self.NORMAL_RESET_FACTOR)
        for score in range(self.MIN_ACT_SCORE, self.MAX_ACT_SCORE+1):
            bull = []
            bear = []
            self.bull = 0
            self.bear = 0
            lastTrendReset = 0
            for candle in datasetCandles:
                def updateTrendScore():
                    change =  candle.getPercentageChange()
                    if candle.bullish:
                        if change > 0 and change < 1:
                            self.bull += 1
                        else:
                            for refChange in range(1, 25):
                                if change <= refChange:
                                    break
                                self.bull += 1
                    else:
                        if change <= 0 and change > -1:
                            self.bear += 1
                        else:
                            for refChange in range(-1, -25):
                                if change >= refChange:
                                    break
                                self.bear += 1

                def resetTrendScore(resetIter):
                    iter = datasetCandles.index(candle)
                    if candle.indicators.get("RSI(14)") - candle.indicators.get("RSI(42)") >= 20 and iter-resetIter >= self.NORMAL_RESET_FACTOR:
                        self.bull = int(score/2)
                    elif candle.indicators.get("RSI(14)") - candle.indicators.get("RSI(42)") <= -20 and iter-resetIter >= self.NORMAL_RESET_FACTOR:
                        self.bear = int(score/2)
                    elif iter % resetFactor == 0 and iter != 0:
                        self.bull = int(score/2)
                        self.bear = int(score/2)
                    return iter
                
                updateTrendScore()
                lastTrendReset = resetTrendScore(lastTrendReset)
                bull.append(self.bull)
                bear.append(self.bear)
                self.bullBias.update({score : bull})
                self.bearBias.update({score : bear})

    def preloadHeikenStrategy(self, heikenCandles = list[BacktestCandle]):
        pass

class BacktestDataset():

    timeframes = {"1m" : 60000, "5m" : 300000, "15m" : 900000, "1h" : 3600000, "6h" : 21600000, "1D" : 86400000} #milliseconds
    markets = ["BTCUSDT", "BTCBUSD", "ETHBTC", "ETHUSDT"]

    def __init__(self):
        self.market = None
        self.timeframe = None
        self.candles: List[BacktestCandle] = []
        self.heikenAshiCandles = [] 
        self.renkoCandles = []
        self.additionalCandles = {}.fromkeys(self.timeframes.keys())
        self.trendStrategy = BacktestTrendStrategy()

    ######################## DATA SHOW AND STATS ####################################

    def displayRandomCandles(self):
        def displayFixedInterval(startingFrom = int):
            print("Normal:\n", self.candles[startingFrom], self.candles[startingFrom+1], self.candles[startingFrom+2])
            print("HeikenAshi:\n", self.heikenAshiCandles[startingFrom], self.heikenAshiCandles[startingFrom+1], self.heikenAshiCandles[startingFrom+2])

        try:
            sample = random.randint(0, len(self.candles)-1)
            displayFixedInterval(sample)
        except IndexError:
            print("No data loaded!")

    def getDatasetStats(self, quantilesValue = int):

        def getSTDforPriceVariation(absolute):
            percentageChanges = []
            for candle in self.candles:
                if absolute:
                    percentageChanges.append(abs(candle.getPercentageChange()))
                else: percentageChanges.append(candle.getPercentageChange())
            return statistics.stdev(percentageChanges)

        def getGroupedDataPoints(groups, absolute):
            percentageChanges = []
            for candle in self.candles:
                if absolute:
                    percentageChanges.append(abs(candle.getPercentageChange()))
                else: percentageChanges.append(candle.getPercentageChange())
            return statistics.quantiles(percentageChanges, n = groups)
        
        if quantilesValue > 1:
            quantiles = getGroupedDataPoints(quantilesValue, True)
            real_quantiles = getGroupedDataPoints(quantilesValue, False)
            quantilesValue = 100/quantilesValue
            statsStr = { "content" : f"Standard Deviation of price variation --> Absolute values: {std_8rounding(getSTDforPriceVariation(True))} %, "
                        + f"Real values: {std_8rounding(getSTDforPriceVariation(False))} %\n"
                        + f"Quantiles absolute extremities --> lower end: {quantilesValue} % less volatile candles moved at max by +/- {std_4rounding(quantiles[0])} %, "
                        + f"higher end: {quantilesValue} % more volatile candles moved at least by +/- {std_4rounding(quantiles[len(quantiles)-1])} %\n"
                        + f"Quantiles real extremities --> lower end: {quantilesValue} % most bearish candles moved at least by {std_4rounding(real_quantiles[0])} %, "
                        + f"higher end: {quantilesValue} % more bullish candles moved at least by {std_4rounding(real_quantiles[len(real_quantiles)-1])} %"
            }
        else: return "Invalid quantiles value!"
        
        return statsStr.get("content")

    ######################### DATA GETTERS  #############################

    def getLoadedDates(self, heiken):
        dates = []
        if heiken: candleSrc = self.heikenAshiCandles
        else: candleSrc = self.candles
        for candle in candleSrc:
            dates.append(timestampToDate(candle.timestamp))
        return numpy.array(dates)

    def getLoadedCloses(self, heiken):
        closes = []
        if heiken: candleSrc = self.heikenAshiCandles
        else: candleSrc = self.candles
        for candle in candleSrc:
            closes.append(candle.close)
        return numpy.array(closes)

    def getLoadedOpens(self, heiken):
        opens = []
        if heiken: candleSrc = self.heikenAshiCandles
        else: candleSrc = self.candles
        for candle in candleSrc:
            opens.append(candle.open)
        return numpy.array(opens)
    
    def getLoadedLows(self, heiken):
        lows = []
        if heiken: candleSrc = self.heikenAshiCandles
        else: candleSrc = self.candles
        for candle in candleSrc:
            lows.append(candle.low)
        return numpy.array(lows)
    
    def getLoadedHighs(self, heiken):
        highs = []
        if heiken: candleSrc = self.heikenAshiCandles
        else: candleSrc = self.candles
        for candle in candleSrc:
            highs.append(candle.high)
        return numpy.array(highs)

    def getLoadedSMA(self, period):
        if period in BacktestCandle.SMAs_periods:
            smaValues = []
            for candle in self.candles:
                smaValues.append(candle.SMAs.get(period))
            return numpy.array(smaValues)
        else: raise AttributeError(f"SMA period {period} is unavailable")

    def getTrendBias(self):
        return (self.trendStrategy.bullBias, self.trendStrategy.bearBias)

    def getHeikenBias(self):
        return self.trendStrategy.heikenBias

    ############################ DATA LOADING #####################################

    def dumpLoadedCandles(self):
        self.candles.clear()
        self.heikenAshiCandles.clear()
        self.renkoCandles.clear()

    def dumpAdditionalLoadedCandles(self):
        self.additionalCandles.clear()

    def loadCandlesFromFile(self, filepath = str):

        def setMarketAndTimeframe():
            for market in self.markets:
                if filepath.find(market) != -1:
                    if self.market == None:
                        self.market = market
                        break
                    elif self.market == market:
                        break
                    else: raise AttributeError("Check filepath market!")
            for timeframe in self.timeframes.keys():
                if filepath.find(timeframe) != -1:
                    if self.timeframe == None:
                        self.timeframe = timeframe
                        break
                    elif self.timeframe == timeframe:
                        break
                    else: raise AttributeError("Check filepath timeframe!")
                    
        def loadHeikenAshi():
            if previouslyLoaded != 0:
                rng = range(previouslyLoaded-1, len(self.candles)-1)
            else: rng = range(previouslyLoaded, len(self.candles)-1)
            for x in rng:
                self.heikenAshiCandles.append(self.candles[x+1].getHeikenAshi(self.candles[x]))

        def addRSIs():
            rsi14Values = talib.RSI(self.getLoadedCloses(False), 14)
            rsi42Values = talib.RSI(self.getLoadedCloses(False), 42)
            numpy.put(rsi14Values, range(0, 14), 0, mode='clip')
            numpy.put(rsi42Values, range(0, 42), 0, mode='clip')
            for x in range(0, len(self.candles)):
                self.candles[x].addValueRSI14(std_4rounding(rsi14Values[x]))
                self.candles[x].addValueRSI42(std_4rounding(rsi42Values[x]))
        
        def addAllMovingAverages():

            def addSMA(period):
                if period in BacktestCandle.SMAs_periods:
                    smaValues = talib.SMA(self.getLoadedCloses(False), period)
                    for x in range(0, len(self.candles)):
                        self.candles[x].addValueSMA(period, std_4rounding(smaValues[x]))

            def addEMA(period):
                if period in BacktestCandle.EMAs_periods:
                    emaValues = talib.EMA(self.getLoadedCloses(False), period)
                    for x in range(0, len(self.candles)):
                        self.candles[x].addValueEMA(period, std_4rounding(emaValues[x]))

            try:
                for period in BacktestCandle.SMAs_periods:
                    if period <= len(self.candles):
                        addSMA(period)
                for period in BacktestCandle.EMAs_periods:
                    if period <= len(self.candles):
                        addEMA(period)

            except IndexError as e:
                print(e.with_traceback(None))

        try:
            setMarketAndTimeframe()
            previouslyLoaded = len(self.candles) 
            candles_file = open(mode='r', file=filepath)
            params = [""]
            while len(params) > 0:
                params.clear()
                params = candles_file.readline().split(sep=',')
                if len(params) >= 5:
                    candle = BacktestCandle(int(params[0]), float(params[1]), float(params[2]), float(params[3]), float(params[4]), isHeiken = False)
                    self.candles.append(candle)
                else: 
                    candles_file.close()
                    break
            
            loadHeikenAshi(), addRSIs(), addAllMovingAverages()
            self.trendStrategy.preloadTrendStrategy(self.candles)
            self.trendStrategy.preloadHeikenStrategy(self.heikenAshiCandles)

        except OSError as e:
            print(e)

    def loadAdditionalCandles(self, filepath = str):
        pass

    def checkLoadedDatesOrder(self):
        correct_order = False
        for x in range(0, len(self.candles)-2):
            if self.candles[x].timestamp < self.candles[x+1].timestamp:
                correct_order = True
            else: 
                correct_order = False
                break
        return correct_order

    def __str__(self):
        if len(self.candles) != 0:
            str = { "content": f"Backtest dataset details --> Market: {self.market}, Timeframe:{self.timeframe}\n"
                    + f"Starting date: {timestampToDate(self.candles[0].timestamp)}, Ending date: {timestampToDate(self.candles[len(self.candles)-1].timestamp)}\n"
                    + f"Additional stats --> Total candles backetested: {len(self.candles)}, max period price: {max(self.getLoadedHighs(False))} $, min period price: {min(self.getLoadedLows(False))} $\n"
                    + f"{self.getDatasetStats(20)}"
            }
        else: return "No loaded candles in the dataset"
        return str.get("content")

class BackTestRunner():

    def __init__(self, loadedDataset = BacktestDataset, timeframe = str, market = str, **kwargs):
        def validPreset():
            try:
                return kwargs.get("initialUSD") >= 10 and 0 <= kwargs.get("startingAllocation") <= 1 and kwargs.get("tpValue") > 0 and (kwargs.get("initialUSD")*kwargs.get("startingAllocation")) > kwargs.get("tradesSizeUSD")
            except Exception:
                raise AttributeError()
        
        if validPreset():
            self.dataset = loadedDataset
            self.timeframe = timeframe
            self.market = market
            self.bot = None
            self.loggingID = 0
            self.runnerSetup(**kwargs)
        else: raise AttributeError()

    def runnerSetup(self, **kwargs):
        self.bot = BacktestBot(self.dataset, kwargs.get("initialUSD"), kwargs.get("tradesSizeUSD"), kwargs.get("startingAllocation"), kwargs.get("tpValue"), 
                   kwargs.get("plottable"), kwargs.get("adaptiveTradesSize"))
    
    def runSimpleStrategyBacktest(self, **kwargs):
        self.bot.applySimpleTrendScoreStrategy(kwargs.get("activationScore"), kwargs.get("maxOpen"), kwargs.get("closingAge"))
    
    def logToTextFile(self):
        self.loggingID = int(datetime.datetime.now().timestamp())
        loggingToFile(loggingFileFormat(self.timeframe, self.market, self.dataset.trendStrategy.name, self.loggingID))
        logData(self.dataset), logData(self.bot)

    def logToTextFileExtended(self):
        self.loggingID = int(datetime.datetime.now().timestamp())
        loggingToFile(loggingFileFormat(self.timeframe, self.market, self.dataset.trendStrategy.name, self.loggingID))
        logData(self.dataset), logData(self.bot)
        for trade in self.bot.trades:
            logData(trade)
        logData("\n")
    
    def getCurrentBotProps(self): 
        return self.bot.getBotPropsDict()

class BacktestBot():

    plotDictKeys = ["buyNholdUSD", "runningBotUSD", "buyNholdPNL", "runningPNL", "runningEff", "bullBias", "bearBias"]

    def __init__(self, dataset = BacktestDataset, initialUSD = int, tradesSizeUSD = int, startingAllocation = float, tpValue = float, plotPerformance = bool, adaptiveTradesSize = bool):

        try:
            def validPreset():
                return initialUSD >= 10 and 0 <= startingAllocation <= 1 and tpValue > 0 and (initialUSD*startingAllocation) > tradesSizeUSD
            
            if validPreset(): 
                #inputs
                self.dataset = dataset
                self.initialUSD = initialUSD
                self.initialCOIN = initialUSD/dataset.candles[0].close
                self.startingTradesSizeUSD = tradesSizeUSD
                self.tradesSizeUSD = tradesSizeUSD
                self.tradesSizeCOIN = tradesSizeUSD/dataset.candles[0].close
                self.startingAllocation = startingAllocation
                self.tpValue = tpValue
                self.plottable: Final[bool] = plotPerformance
                self.adaptiveTrades: Final[bool] = adaptiveTradesSize

                #live position
                self.positionUSD = initialUSD*startingAllocation
                self.positionCOIN = self.initialCOIN*(1-startingAllocation)
                self.trades: List[BacktestTrade] = []
                self.failedOnOpen = 0
                self.failedTP = 0
                self.failedSL = 0
                if self.plottable:
                    self.plotSrc = { str : list }.fromkeys(self.plotDictKeys)
                    self.buyNholdTrade = BacktestTrade(dataset.candles[0].timestamp, True, dataset.candles[0].close, self.initialCOIN)
                if self.adaptiveTrades:
                    self.tradeSizeRatio = std_2rounding(self.tradesSizeUSD/self.initialUSD)
                
                #final outputs
                self.strategy = None
                self.totalFeesUSD = 0
                self.finalUSD = 0
                self.finalOnestUSD = 0
                self.botPNL = 0
                self.botEfficency = 0
                
            else: raise AttributeError()
        except IndexError or AttributeError:
            print("Check input parameters")

    def resetBot(self):
        #live position
        self.positionUSD = self.initialUSD*self.startingAllocation
        self.positionCOIN = self.initialCOIN*(1-self.startingAllocation)
        self.trades.clear()
        self.failedOnOpen = 0
        self.failedTP = 0
        self.failedSL = 0
        if self.plottable:
            self.plotSrc.clear()
            self.buyNholdTrade = BacktestTrade(self.dataset.candles[0].timestamp, True, self.dataset.candles[0].close, self.initialCOIN)
        if self.adaptiveTrades:
            self.tradesSizeUSD = self.startingTradesSizeUSD

        #final outputs
        self.totalFeesUSD = 0
        self.finalUSD = 0
        self.finalOnestUSD = 0
        self.botPNL = None
        self.botEfficency = None
    
    def resetBotAndChangeDataset(self, newDataset = BacktestDataset):
        self.dataset = newDataset
        self.resetBot()

    def getProfitableTrades(self):
        profitable = 0
        for trade in self.trades:
            if trade.isClosed():
                if trade.rawPNL > 0:
                    profitable += 1
        return profitable

    def currentTradesOpen(self):
        open = 0
        for trade in self.trades:
            if not trade.isClosed():
                open += 1
        return open

    #AUTOTRADER
    def updateTradesSize(self, currentPrice):
        self.tradesSizeUSD = std_2rounding((self.positionUSD + (self.positionCOIN*currentPrice))*self.tradeSizeRatio)

    def openLong(self, time = int, price = float):
        if self.positionUSD >= self.tradesSizeUSD:
            newTrade = BacktestTrade(time, True, price, self.tradesSizeUSD/price)
            self.trades.append(newTrade)
            self.positionUSD -= newTrade.qtyUSD
            self.positionCOIN += newTrade.qty
            self.checkNegativeBalance(newTrade)
            return True
        else: 
            self.failedOnOpen += 1
            return False

    def openShort(self, time = int, price = float):
        if self.positionCOIN >= self.tradesSizeCOIN:
            newTrade = BacktestTrade(time, False, price, self.tradesSizeUSD/price)
            if self.positionCOIN >= newTrade.qty:
                self.trades.append(newTrade)
                self.positionUSD += newTrade.qtyUSD
                self.positionCOIN -= newTrade.qty
                self.checkNegativeBalance(newTrade)
                return True
            else: 
                self.failedOnOpen += 1
                return False
        else: 
            self.failedOnOpen += 1
            return False

    def canCloseLong(self, trade = BacktestTrade):
        if self.positionCOIN > trade.qty:
            return True
        else: 
            self.failedTP += 1
            return False
        
    def canCloseShort(self, trade = BacktestTrade):
        if self.positionUSD > trade.qtyUSD:
            return True
        else: 
            self.failedTP += 1
            return False

    def closeLong(self, trade = BacktestTrade):
        self.positionUSD += trade.pnlUSD + trade.qtyUSD
        self.positionCOIN -= trade.qty 
        self.checkNegativeBalance(trade)
        
    def closeShort(self, trade = BacktestTrade):
        self.positionUSD -= trade.qtyUSD
        self.positionCOIN += trade.pnlQTY + trade.qty
        self.checkNegativeBalance(trade)

    def SLRound(self, currentPrice, currentTime, closingAge):
        closable = []
        pnls = []
        try:
            for trade in self.trades:
                if not trade.isClosed():
                    if trade.getAgeInCandles(currentTime, self.dataset.timeframe) >= closingAge:
                        closable.append(trade)
                        pnls.append(trade.getPNL(currentPrice))
            bestPnl = max(pnls)
            toBeClosed = None
            for trade in closable:
                if bestPnl == trade.getPNL(currentPrice):
                    toBeClosed = trade
                    if toBeClosed.isBuy and self.canCloseLong(toBeClosed):
                        toBeClosed.closeTrade(currentPrice, currentTime)
                        self.closeLong(toBeClosed)
                    elif self.canCloseShort(toBeClosed):
                        toBeClosed.closeTrade(currentPrice, currentTime)
                        self.closeShort(toBeClosed)
                    break

        except ValueError:
            pass

    def TPRound(self, currentPrice, currentTime):
        for trade in self.trades:
            if not trade.isClosed():                                                     
                if trade.getPNL(currentPrice) >= self.tpValue:
                    if trade.isBuy and self.canCloseLong(trade):
                        trade.closeTrade(currentPrice, currentTime)
                        self.closeLong(trade)
                    elif self.canCloseShort(trade):
                        trade.closeTrade(currentPrice, currentTime)
                        self.closeShort(trade)

    def checkNegativeBalance(self, originTrade):
        if self.positionUSD < 0 or self.positionCOIN < 0: raise RuntimeError(f"{self.positionUSD} and {self.positionCOIN} resulted negative after this trade:\n{originTrade.__str__()}")

    def closeBestTradeUnderTP(self, currentPrice, currentTime):
        closable = []
        pnls = []
        try:
            for trade in self.trades:
                if not trade.isClosed():
                    pnl = trade.getPNL(currentPrice)
                    if pnl > 0 and pnl < self.tpValue: #best case
                        closable.append(trade)
                        pnls.append(pnl)
            bestPnl = max(pnls)
        except ValueError:
            try:
                for trade in self.trades:
                    if not trade.isClosed():
                        pnl = trade.getPNL(currentPrice)
                        if pnl >= -self.tpValue and pnl <= 0: #bad case
                            closable.append(trade)
                            pnls.append(pnl)
                bestPnl = max(pnls)
            except ValueError:
                for trade in self.trades:
                    if not trade.isClosed():
                        closable.append(trade) 
                        pnls.append(trade.getPNL(currentPrice))   #worst case
                bestPnl = max(pnls)

        finally:
            toBeClosed = None
            for trade in closable:
                if bestPnl == trade.getPNL(currentPrice):
                    toBeClosed = trade
                    if toBeClosed.isBuy and self.canCloseLong(toBeClosed):
                        toBeClosed.closeTrade(currentPrice, currentTime)
                        self.closeLong(toBeClosed)
                        return True
                    elif self.canCloseShort(toBeClosed):
                        toBeClosed.closeTrade(currentPrice, currentTime)
                        self.closeShort(toBeClosed)
                        return True
                    break
            return False
        
    def closeRemainingTrades(self):
        for trade in self.trades:
            if not trade.isClosed():            
                if trade.isBuy and self.canCloseLong(trade):
                    trade.closeTrade(self.dataset.candles[len(self.dataset.candles)-1].close, self.dataset.candles[len(self.dataset.candles)-1].timestamp)
                    self.closeLong(trade)
                elif self.canCloseShort(trade): 
                    trade.closeTrade(self.dataset.candles[len(self.dataset.candles)-1].close, self.dataset.candles[len(self.dataset.candles)-1].timestamp)
                    self.closeShort(trade)

    #STRATEGIES
    def applySimpleTrendScoreStrategy(self, activationScore, maxOpen, closingAge):
        if len(self.trades) == 0:
            bullBias = self.dataset.getTrendBias()[0].get(activationScore)
            bearBias = self.dataset.getTrendBias()[1].get(activationScore)
            if self.plottable:
                self.plotSrc.update({"bullBias" : bullBias, "bearBias" : bearBias})
                bNhUSD = []
                bNhPNLS = []
                totalUSD = [] 
                pnls = []
                efficencies = []

            for candle in self.dataset.candles:
                currentPrice = candle.close
                currentTime = candle.timestamp
                bullValue = bullBias[self.dataset.candles.index(candle)]
                bearValue = bearBias[self.dataset.candles.index(candle)]
                
                def updatePlottableData():
                    if self.plottable:
                        currentTotal = self.positionUSD + (self.positionCOIN*currentPrice)
                        bNhUSD.append(std_2rounding((1 + (self.buyNholdTrade.getPNL(currentPrice)/100))*self.buyNholdTrade.qtyUSD))
                        bNhPNLS.append(std_4rounding(self.buyNholdTrade.getPNL(currentPrice)))
                        totalUSD.append(std_2rounding(currentTotal)), pnls.append(std_4rounding(((currentTotal/self.initialUSD)-1)*100))
                        efficencies.append(std_4rounding((((self.positionUSD + (self.positionCOIN*self.dataset.candles[0].close))/self.initialUSD)-1)*100))
                        self.plotSrc.update({"buyNholdUSD" : bNhUSD, "buyNholdPNL" : bNhPNLS, "runningBotUSD" : totalUSD, "runningPNL" : pnls, "runningEff" : efficencies})

                def tradeOpenerByBias():
                    if self.currentTradesOpen() <= maxOpen:
                        if bullValue > activationScore:
                            return self.openLong(currentTime, currentPrice)
                        if bearValue> activationScore:
                            return self.openShort(currentTime, currentPrice)
                    else: return self.closeBestTradeUnderTP(currentPrice, currentTime)
                
                tradeOpenerByBias()
                self.TPRound(currentPrice, currentTime)
                self.SLRound(currentPrice, currentTime, closingAge)
                if self.adaptiveTrades:
                    self.updateTradesSize(currentPrice)
                updatePlottableData()

            self.closeRemainingTrades()
            self.strategy = (activationScore, maxOpen, closingAge)
            self.setFinalOutputs()

        else: raise RuntimeError("This strategy has already been applied to the dataset!")

    def applyHeikenAshiStrategy(self, maxOpen, closingAge):
        pass

    def applyRenkoStrategy(self):
        pass

    #RESULTS
    def setFinalOutputs(self):
        self.finalUSD = self.positionUSD + (self.positionCOIN*self.dataset.candles[len(self.dataset.candles)-1].close)
        self.finalOnestUSD = self.positionUSD + (self.positionCOIN*self.dataset.candles[0].close)
        self.totalFeesUSD = (len(self.trades)*2*FEES_VALUE)*self.tradesSizeUSD
        self.finalUSD -= self.totalFeesUSD
        self.botPNL = ((self.finalUSD/self.initialUSD)-1)*100
        self.botEfficency = ((self.finalOnestUSD/self.initialUSD)-1)*100

        def updateFinalPlottableData():
            if self.plottable:
                self.plotSrc.get("runningBotUSD").pop()
                self.plotSrc.get("runningBotUSD").append(self.finalUSD)
                self.plotSrc.get("runningPNL").pop()
                self.plotSrc.get("runningPNL").append(self.botPNL)
                self.plotSrc.get("runningEff").pop()
                self.plotSrc.get("runningEff").append(self.botEfficency)
        
        updateFinalPlottableData()

    def getBotPropsDict(self):
        botProps = {"startUSD":self.initialUSD, 
                    "plottable":self.plottable,
                    "adaptiveTrades":self.adaptiveTrades,
                    "tradeSize":self.startingTradesSizeUSD, 
                    "allocation":self.startingAllocation, 
                    "tp":self.tpValue,
                    "strategy":self.strategy, 
                    "finalUSD":self.finalUSD, 
                    "finalNormUSD":self.finalOnestUSD, 
                    "totalTrades":len(self.trades), 
                    "winTrades":self.getProfitableTrades(),
                    "logStr":self.__str__()
                }
        
        if self.adaptiveTrades: 
            botProps.update({"tradesSizeRatio":self.tradeSizeRatio})
        if self.plottable:
            botProps.update({"plotData":self.plotSrc})
        
        return botProps

    def __str__(self):
        if len(self.trades) > 0:
            try:                
                str = {
                    "content" : f"Backtest results overivew (Timeframe: {self.dataset.timeframe}, Market: {self.dataset.market}):\n"
                    + f"Starting USD equivalent: {self.initialUSD} $ --> ({std_2rounding(self.initialUSD*self.startingAllocation)} $, {std_8rounding(self.initialCOIN*(1-self.startingAllocation))} COIN), "
                    + f"Final USD equivalent: {std_2rounding(self.finalUSD)} $ --> ({std_2rounding(self.positionUSD)} $, {std_8rounding(self.positionCOIN)} COIN) --> "
                    + f"Normalized to starting price: {std_2rounding(self.finalOnestUSD)} $\nFinal price based PNL: {std_4rounding(self.botPNL)} %, Starting price based PNL/Efficency: {std_4rounding(self.botEfficency)} %\n"
                    + f"Total trades: {len(self.trades)} of which {self.getProfitableTrades()} were profitable, Failed to open {self.failedOnOpen} trades, Failed to close {self.failedTP+self.failedSL} times\n"
                    + f"Trades size: {self.startingTradesSizeUSD} $ ({std_8rounding(self.tradesSizeCOIN)} COIN), Take profit value used: {self.tpValue} %, Total fees paid: {std_2rounding(self.totalFeesUSD)} $\n"
                    + f"Simple strategy tuple: [long/short trade activation score: {self.strategy[0]}, max trades open at the same time: {self.strategy[1]}, max time open for each position: {self.strategy[2]} candles]\n"
                }
            except ValueError:
                pass
            return str.get("content")
        else: return "This strategy has 0 trades attached\n"

class BacktestLeveragedBot(BacktestBot):

    def __init__(self, dataset=BacktestDataset, initialUSD=int, tradesSizeUSD=int, startingAllocation=float, tpValue=float, plotPerformance=bool, 
                 adaptiveTradesSize=bool, leverage=float, adaptiveLeverage = bool):
        self.leverage = leverage
        if adaptiveLeverage:
            self.riskFactor = std_2rounding((initialUSD/leverage)/initialUSD)
        super().__init__(dataset, initialUSD, tradesSizeUSD, startingAllocation, tpValue, plotPerformance, adaptiveTradesSize)

#OPTIMIZER
class BacktestStrategyOptimizer():

    minScore = 10
    minOpen = 10
    minAge = 10

    def __init__(self, loadedDataset = BackTestLoader):
        self.loadedDataset = loadedDataset
        self.bots: List[str] = []
        self.botsPNLs: List[float] = []
        self.botsEfficencies: List[float] = []
        self.stategyParams: List[tuple] = []
        self.bestPNL = None
        self.bestEfficency = None
        self.winningBots = 0 #calculated by efficency
        self.losingBots = 0 #calculated by efficency
        self.WLratio = 0 #calculated by efficency
        self.totalPossibleConfigs = 0
        self.validConfigs = 0
        self.invalidConfigs = 0
        self.failedConfigs = 0

    def validOptimization(self):
        return len(self.bots) == len(self.botsPNLs) == len(self.botsEfficencies) == len(self.stategyParams)

    def setWinLoseRatio(self):
        for bot in self.bots:
            if bot.find("Strategy Efficency: -") != -1:
                self.losingBots += 1
        self.winningBots = len(self.bots) - self.losingBots
        if self.losingBots != 0:
            self.WLratio = std_2rounding(self.winningBots/self.losingBots)
        else: self.WLratio = float('inf')

    def setBestBotByPNL(self):
        for bot in self.bots:
            if bot.find(f"Final price based PNL: {std_4rounding(max(self.botsPNLs))} %") != -1:
                self.bestPNL = bot
                break

    def setBestBotByEfficency(self):
        for bot in self.bots:
            if bot.find(f"Starting price based PNL/Efficency: {std_4rounding(max(self.botsEfficencies))} %") != -1:
                self.bestEfficency = bot
                break

    def randomizeSimpleStrategyParams(self, maxTP, maxScore, maxMaxOpen, maxClosingAge): #very heavy method, range step between input parameters is 1
        if self.loadedDataset.ready:
            def validRandomizationLimits():
                return maxTP >= MINIMAL_TP and maxScore > self.minScore and maxMaxOpen > self.minOpen and maxClosingAge > self.minAge
            
            if  validRandomizationLimits():
                runner =  BackTestRunner(self.loadedDataset.dataset, self.loadedDataset.dataset.timeframe, self.loadedDataset.dataset.market, initialUSD = DEFAULT_INITAL, 
                                         tradesSizeUSD = DEFAULT_TRADES_SIZE, startingAllocation = ALLOCATION_50_50, tpValue = maxTP, plottable = False, adaptiveTradesSize = False)
                validBots = []
                pnls = []
                efficencies = []
                params = []

                with ProgressBar(max_value=(maxScore-self.minScore)*(maxMaxOpen-self.minOpen)*(maxClosingAge-self.minAge)) as bar:
                    barValue = 0
                    barFull = False
                    for score in range(self.minScore, maxScore+1):
                        for open in range(self.minOpen, maxMaxOpen+1):
                            for age in range(self.minAge, maxClosingAge+1):
                                try:
                                    self.totalPossibleConfigs += 1
                                    runner.runSimpleStrategyBacktest(activationScore = score, maxOpen = open, closingAge = age)
                                    validBots.append(runner.bot.__str__())
                                    pnls.append(runner.bot.botPNL)
                                    efficencies.append(runner.bot.botEfficency)
                                    params.append(runner.bot.strategy)
                                    runner.bot.resetBot()
                                    self.validConfigs += 1
                                except RuntimeError or AttributeError:
                                    self.failedConfigs += 1
                                    runner.bot.resetBot()
                                finally:
                                    try:
                                        if not barFull:
                                            bar.update(barValue)
                                            barValue += 1
                                    except ValueError:
                                        print("\nBacktest optimization completed! Fetching results...\n")
                                        barFull = True
                                    continue
                
                self.bots.extend(validBots)
                self.botsPNLs.extend(pnls)
                self.botsEfficencies.extend(efficencies)
                self.stategyParams.extend(params)

                if self.validOptimization():
                    self.validConfigs = len(self.bots)
                    self.setWinLoseRatio()
                    self.setBestBotByPNL()
                    self.setBestBotByEfficency()
                else: raise RuntimeError("Inconsistent bot data generated!")
            else: raise AttributeError("Check input attributes")

        else: raise AttributeError("Check the loaded dataset!")

    def __str__(self):
        if len(self.bots) != 0:
            str = { "content" : f"{self.loadedDataset.dataset.__str__()}\n\nStrategy optimization results:\nTotal tried configuration: {self.validConfigs} out of {self.totalPossibleConfigs} possible --> "
                   + f"({self.winningBots} with positive Efficency, {self.losingBots} with negative Efficency, {self.failedConfigs} failed to run) --> Win-Lose ratio: {self.WLratio}"
                   + f"\n\nOptimal bot configuration by PNL:\n{self.bestPNL}\nOptimal bot configuration by Efficency:\n{self.bestEfficency}"  
                }
            return str.get("content")
        else: return "No strategy iterated!"
            
class BacktestGraph():

    def __init__(self, runnedBacktest = BackTestRunner):
        self.backtestID = runnedBacktest.loggingID
        self.dataset = runnedBacktest.dataset
        self.performanceData = runnedBacktest.bot.plotSrc
        self.strategyData = runnedBacktest.bot.strategy
        self.trendStrategyData = runnedBacktest.dataset.trendStrategy
        self.xDates = self.dataset.getLoadedDates(False)
        self.linePlot = make_subplots(specs=[[{"secondary_y": True}]])
        self.candlePlot = make_subplots(specs=[[{"secondary_y": True}]])
        self.heikenPlot = make_subplots(specs=[[{"secondary_y": True}]])
        self.performancePlot = None
        self.loaded = False
        self.setupPriceData()
    
    def setupPriceData(self):
        self.linePlot.add_trace(go.Scatter(x = self.xDates, y = self.dataset.getLoadedCloses(False), name = self.dataset.market + " price"), secondary_y = False)
        self.candlePlot.add_trace(go.Candlestick(x = self.xDates, close = self.dataset.getLoadedCloses(False), open = self.dataset.getLoadedOpens(False),
                                high = self.dataset.getLoadedHighs(False), low = self.dataset.getLoadedLows(False), name = self.dataset.market + " price"), secondary_y = False)
        self.heikenPlot.add_trace(go.Candlestick(x = self.dataset.getLoadedDates(True), close = self.dataset.getLoadedCloses(True), open = self.dataset.getLoadedOpens(True),
                                high = self.dataset.getLoadedHighs(True), low = self.dataset.getLoadedLows(True), name = self.dataset.market + " price"), secondary_y = False)

    def resetGraphData(self):
        self.linePlot = make_subplots(specs=[[{"secondary_y": True}]])
        self.candlePlot = make_subplots(specs=[[{"secondary_y": True}]])
        self.heikenPlot = make_subplots(specs=[[{"secondary_y": True}]])
        self.performancePlot = None
        self.loaded = False
        self.setupPriceData()

    def showPriceDatatWithMA(self, MAperiod1 = int, MAperiod2 = int): 
        if MAperiod1 in BacktestCandle.SMAs_periods and MAperiod2 in BacktestCandle.SMAs_periods:
            self.candlePlot.add_trace(go.Scatter(x = self.xDates, y = self.dataset.getLoadedSMA(MAperiod1), name = f"{MAperiod1} SMA", 
                                      line = { "color" : "blue"}), secondary_y = False)
            self.candlePlot.add_trace(go.Scatter(x = self.xDates, y = self.dataset.getLoadedSMA(MAperiod2), name = f"{MAperiod2} SMA", 
                                      line = { "color" : "gold"}), secondary_y = False)
            self.candlePlot.update_layout(title = self.dataset.market + " simple candle graph", yaxis_title = "Price ($)")
            self.candlePlot.update_yaxes(type = "log")
            self.candlePlot.show()

    def showPriceDataWithHeikenAshi(self):
        #self.heikenPlot.add_trace(go.Scatter(x = self.xDates, y = self.dataset.getLoadedCloses(False), name = "normal candle closing price",
                                  #line = { "color" : "orange"}), secondary_y = False)
        self.heikenPlot.update_layout(title = self.dataset.market + " simple candle graph", yaxis_title = "Price ($)")
        self.heikenPlot.update_yaxes(type = "log")
        self.heikenPlot.show()

    def showBacktest(self):
        if self.loaded:
            self.performancePlot.show()
        else: raise  RuntimeError("Backtest data is not loaded on the plot!") 

    def loadUSDequivalentsOnGraph(self, withCandles = bool):
        if withCandles:
            self.performancePlot = self.candlePlot
        else: self.performancePlot = self.linePlot
        self.performancePlot.add_trace(go.Scatter(x = self.xDates, y = numpy.array(self.performanceData.get("buyNholdUSD")), name = "Running buy and hold trade USD equivalent", 
                                                line = { "color" : "orange"}), secondary_y = True)
        self.performancePlot.add_trace(go.Scatter(x = self.xDates, y = numpy.array(self.performanceData.get("runningBotUSD")), name = "Running bot total USD equivalent", 
                                                line = { "color" : "darkgrey"}), secondary_y = True)
        self.performancePlot.update_layout(title = f"Perfromance of backtest on {self.dataset.market} with timestamp/ID: {self.backtestID}", yaxis_title = "Price ($)")
        self.performancePlot.update_yaxes(type = "log", secondary_y = False)
        self.loaded = True

    def loadPerformanceOnGraph(self, withCandles = bool):
        if withCandles:
            self.performancePlot = self.candlePlot
        else: self.performancePlot = self.linePlot
        self.performancePlot.add_trace(go.Scatter(x = self.xDates, y = numpy.array(self.performanceData.get("buyNholdPNL")), name = "Running buy and hold trade PNL (%)",
                                                line = { "color" : "orange"}), secondary_y = True)
        self.performancePlot.add_trace(go.Scatter(x = self.xDates, y = numpy.array(self.performanceData.get("runningPNL")), name = "Running PNL (%)",
                                                line = { "color" : "darkgrey"}), secondary_y = True)
        self.performancePlot.add_trace(go.Scatter(x = self.xDates, y = numpy.array(self.performanceData.get("runningEff")), name = "Running Efficency (%)",
                                                line = { "color" : "purple"}), secondary_y = True)
        self.performancePlot.update_layout(title = f"Perfromance of backtest on {self.dataset.market} with timestamp/ID: {self.backtestID}", yaxis_title = "Price ($)")
        self.performancePlot.update_yaxes(type = "log", secondary_y = False)
        self.loaded = True

#STRATEGIES



    
    

    
    
    
