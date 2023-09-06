#do this bruh U got this, anyway.. godspeed!#
#AUTHOR: TrippyBruh#
import talib, random, statistics, numpy
from typing import List
from plotly import graph_objects as go
from plotly import express as ex
from BacktesterCore.AlgoTradeHelpers import *

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
        return BacktestCandle(previousCandle.timestamp, (previousCandle.open + previousCandle.close)/2, max(self.high, self.open, self.close), 
               min(self.low, self.open, self.close), (self.open + self.high + self.low + self.close)/4, isHeiken = True)

    def getAllIndicators(self):
        return self.indicators.values()

    def getAllSMAs(self):
        return self.SMAs.values()
    
    def getAllEMAs(self):
        return self.EMAs.values()

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

class BacktestPortfolio():
    
    assets = ["USD", "BTC", "ETH", "ADA"]

    portfolio1 = {"USD" : 0.5,
                  "BTC" : 0.3,
                  "ETH" : 0.2,
                  "ADA" : 0.1
                }
    portfolio2 = {"USD" : 0.25,
                  "BTC" : 0.4,
                  "ETH" : 0.25,
                  "ADA" : 0.1
                }
    portfolio3 = {"USD" : 0.2,
                  "BTC" : 0.5,
                  "ETH" : 0.25,
                  "ADA" : 0.05
                }
    portfolio4 = {"USD" : 0.5,
                "BTC" : 0.5,
                "ETH" : 0.0,
                "ADA" : 0.0
                }

    def __init__(self, allocatedAssets = dict):
        self.portfolio = {}.fromkeys(self.assets)
        self.portfolio = allocatedAssets.copy()
        allocation = 0
        for allocationValue in self.portfolio.items():
            allocation += allocationValue
        if allocation != 1: raise AttributeError("Total allocation factors must add up to exactly 1")

#LOADING AND RUNNING         
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

    ######################## DATA SHOW AND STATS ####################################

    def getSimpleLineData(self):
        return ex.line(x = self.getLoadedDates(self.candles), y = self.getLoadedCloses(self.candles))

    def getAllCandleData(self, **kwargs):
        normalPlot = go.Figure(data = go.Candlestick(x = self.getLoadedDates(self.candles), close = self.getLoadedCloses(self.candles), open = self.getLoadedOpens(self.candles),
                     high = self.getLoadedHighs(self.candles), low = self.getLoadedLows(self.candles)))
        #heikenPlot = go.Figure(data = go.Candlestick(x = self.getLoadedDates(self.heikenAshiCandles), close = self.getLoadedCloses(self.heikenAshiCandles), open = self.getLoadedOpens(self.heikenAshiCandles),
                     #high = self.getLoadedHighs(self.heikenAshiCandles), low = self.getLoadedLows(self.heikenAshiCandles)))
        #normalPlot.add_trace(go.Scatter(x = self.getLoadedDates(self.candles), y = self.getLoadedSMA(kwargs.get('SMAperiod1')), name = f"{kwargs.get('SMAperiod1')} SMA"))
        #normalPlot.add_trace(go.Scatter(x = self.getLoadedDates(self.candles), y = self.getLoadedSMA(kwargs.get('SMAperiod2')), name = f"{kwargs.get('SMAperiod2')} SMA"))
        normalPlot.update_layout(title = self.market, yaxis_title = "Price ($)")
        return normalPlot

    def displayFixedInterval(self, startingFrom = int):
        print("Normal:\n", self.candles[startingFrom], self.candles[startingFrom+1], self.candles[startingFrom+2])
        print("HeikenAshi:\n", self.heikenAshiCandles[startingFrom], self.heikenAshiCandles[startingFrom+1], self.heikenAshiCandles[startingFrom+2])

    def displayRandomCandle(self):
        try:
            sample = random.randint(0, len(self.candles)-1)
            print(self.candles[sample])
            print(self.heikenAshiCandles[sample])
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

    def getLoadedDates(self):
        dates = []
        for candle in self.candles:
            dates.append(timestampToDate(candle.timestamp))
        return numpy.array(dates)

    def getLoadedCloses(self):
        closes = []
        for candle in self.candles:
            closes.append(candle.close)
        return numpy.array(closes)

    def getLoadedOpens(self):
        opens = []
        for candle in self.candles:
            opens.append(candle.open)
        return numpy.array(opens)
    
    def getLoadedLows(self):
        lows = []
        for candle in self.candles:
            lows.append(candle.low)
        return numpy.array(lows)
    
    def getLoadedHighs(self):
        highs = []
        for candle in self.candles:
            highs.append(candle.high)
        return numpy.array(highs)

    def getLoadedSMA(self, period):
        if period in BacktestCandle.SMAs_periods:
            smaValues = []
            for candle in self.candles:
                smaValues.append(candle.SMAs.get(period))
            return numpy.array(smaValues)
        else: raise AttributeError(f"SMA period {period} is unavailable")

    ####################### DATA AVG/IND GENERATION ###############################

    def addAllIndicators(self):

        def addRSIs():
            rsi14Values = talib.RSI(self.getLoadedCloses(), 14)
            rsi42Values = talib.RSI(self.getLoadedCloses(), 42)
            numpy.put(rsi14Values, range(0, 14), 0, mode='clip')
            numpy.put(rsi42Values, range(0, 42), 0, mode='clip')
            for x in range(0, len(self.candles)):
                self.candles[x].addValueRSI14(std_4rounding(rsi14Values[x]))
                self.candles[x].addValueRSI42(std_4rounding(rsi42Values[x]))
        
        addRSIs()
        
    def addAllMovingAverages(self):

        def addSMA(period):
            if period in BacktestCandle.SMAs_periods:
                smaValues = talib.SMA(self.getLoadedCloses(), period)
                for x in range(0, len(self.candles)):
                    self.candles[x].addValueSMA(period, std_4rounding(smaValues[x]))

        def addEMA(period):
            if period in BacktestCandle.EMAs_periods:
                emaValues = talib.EMA(self.getLoadedCloses(), period)
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

    ############################ DATA LOADING #####################################

    def dumpLoadedCandles(self):
        self.candles.clear()

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

        def fixTimestamp():
            for timeframe in self.timeframes: 
                if filepath.find(timeframe) != -1:
                    return self.timeframes.get(timeframe)
            raise AttributeError("Check filepath timeframe!")
                    
        def loadHeikenAshi():
            if previouslyLoaded != 0:
                rng = range(previouslyLoaded-1, len(self.candles)-1)
            else: rng = range(previouslyLoaded, len(self.candles)-1)
            for x in rng:
                self.heikenAshiCandles.append(self.candles[x+1].getHeikenAshi(self.candles[x]))

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
            loadHeikenAshi()
            
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
                    + f"Additional stats --> Total candles backetested: {len(self.candles)}, max period price: {max(self.getLoadedHighs())} $, min period price: {min(self.getLoadedLows())} $\n"
                    + f"{self.getDatasetStats(20)}"
            }
        else: return "No loaded candles in the dataset"
        return str.get("content")

class BackTestLoader():

    def __init__(self):
        self.dataset = BacktestDataset()
        self.ready = False
    
    def checkReady(self):
        if self.dataset.checkLoadedDatesOrder():
            self.ready = True
        else: 
            self.dataset.dumpLoadedCandles()
            raise RuntimeError("Error in candles timestamps!")

    def loadYearlyBacktest(self, timeframe, market, startingYear, extraYears):
        if extraYears >= 1:
            for x in range(extraYears):
                self.dataset.loadCandlesFromFile(candlesDataFilepath(timeframe, market, f"{startingYear + x}"))
        else: self.dataset.loadCandlesFromFile(candlesDataFilepath(timeframe, market, f"{startingYear}"))

        self.dataset.addAllIndicators()
        self.dataset.addAllMovingAverages()
        self.checkReady()
    
    def loadMonthlyBacktest(self):
        pass

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
            self.setNewBotParameters(**kwargs)
        else: raise AttributeError()

    def setNewBotParameters(self, **kwargs):
        self.bot = BacktestStrategyBot(self.dataset, kwargs.get("initialUSD"), kwargs.get("tradesSizeUSD"), kwargs.get("startingAllocation"), kwargs.get("tpValue"))
    
    def runSimpleStrategyBacktest(self, **kwargs):
        self.bot.applySimpleTrendScoreStrategy(kwargs.get("activationScore"), kwargs.get("maxOpen"), kwargs.get("closingAge"))


    def reloadFreshRunner(self):
        if self.bot != None:
            self.bot = self.bot.getFreshRunner()
        else: raise RuntimeError()

    def botRawEfficency(self):
        return self.bot.botPNL
    
    def logToTextFile(self, strategy = str):
        loggingToFile(loggingFilepath(self.timeframe, self.market, strategy))
        logData(self.bot)

    def logToTextFileExtended(self, strategy = str):
        loggingToFile(loggingFilepath(self.timeframe, self.market, strategy))
        logData(self.dataset), logData(self.bot)
        for trade in self.bot.trades:
            logData(trade)
        logData("\n")

class BacktestStrategyBot():

    def __init__(self, dataset = BacktestDataset, initialUSD = int, tradesSizeUSD = int, startingAllocation = float, tpValue = float, **kwargs):

        self.FEES_VALUE = 0.001 #% factor

        try:
            def validPreset():
                return initialUSD >= 10 and 0 <= startingAllocation <= 1 and tpValue > 0 and (initialUSD*startingAllocation) > tradesSizeUSD
            
            if validPreset(): 
                #inputs
                self.dataset = dataset
                self.initialUSD = initialUSD
                self.initialCOIN = initialUSD/dataset.candles[0].close
                self.tradesSizeUSD = tradesSizeUSD
                self.tradesSizeCOIN = tradesSizeUSD/self.dataset.candles[0].close
                self.startingAllocation = startingAllocation
                self.tpValue = tpValue

                #live position
                self.positionUSD = initialUSD*startingAllocation
                self.positionCOIN = self.initialCOIN*(1-startingAllocation)
                self.runningValue = []
                self.trades: List[BacktestTrade] = []
                self.failedTrades = []
                self.failedTP = 0
                self.failedSL = 0
                
                #final outputs
                self.totalFeesUSD = 0
                self.finalUSD = 0
                self.botPNL = None

                # strategy
                self.bullBias = 0
                self.bearBias = 0
                self.simpleStrat = tuple()
                
            else: raise AttributeError()
        except IndexError or AttributeError:
            print("Check input parameters")

    def resetBot(self):
        #live position
        self.positionUSD = self.initialUSD*self.startingAllocation
        self.positionCOIN = self.initialCOIN*(1-self.startingAllocation)
        self.runningValue.clear()
        self.trades.clear()
        self.failedTrades.clear()
        self.failedTP = 0
        self.failedSL = 0
        #final outputs
        self.totalFeesUSD = 0
        self.finalUSD = 0
        self.botPNL = None
        # strategy
        self.bullBias = 0
        self.bearBias = 0
        self.simpleStrat = tuple()

    def getFreshRunner(self):
        return BacktestStrategyBot(self.dataset, self.initialUSD, self.tradesSizeUSD, self.startingAllocation, self.tpValue)
    
    def currentTradesOpen(self):
        open = 0
        for trade in self.trades:
            if not trade.isClosed():
                open += 1
        return open

    def openLong(self, time = int, price = float):
        newTrade = BacktestTrade(time, True, price, self.tradesSizeUSD/price)
        if self.positionUSD >= self.tradesSizeUSD:
            self.trades.append(newTrade)
            self.positionUSD -= newTrade.qtyUSD
            self.positionCOIN += newTrade.qty
            self.checkNegativeBalance(newTrade)
        else: self.failedTrades.append(newTrade)

    def openShort(self, time = int, price = float):
        newTrade = BacktestTrade(time, False, price, self.tradesSizeUSD/price)
        if self.positionCOIN >= self.tradesSizeCOIN:
            self.trades.append(newTrade)
            self.positionUSD += newTrade.qtyUSD
            self.positionCOIN -= newTrade.qty
            self.checkNegativeBalance(newTrade)
        else: self.failedTrades.append(newTrade)

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
                    break
            if toBeClosed.isBuy and self.canCloseLong(toBeClosed):
                toBeClosed.closeTrade(currentPrice, currentTime)
                self.closeLong(toBeClosed)
            elif self.canCloseShort(toBeClosed):
                toBeClosed.closeTrade(currentPrice, currentTime)
                self.closeShort(toBeClosed)
        
    def closeRemainingTrades(self):
        
        def closingRun():
            for trade in self.trades:
                if not trade.isClosed():            
                    if trade.isBuy and self.canCloseLong(trade):
                        trade.closeTrade(self.dataset.candles[len(self.dataset.candles)-1].close, self.dataset.candles[len(self.dataset.candles)-1].timestamp)
                        self.closeLong(trade)
                    elif self.canCloseShort(trade): 
                        trade.closeTrade(self.dataset.candles[len(self.dataset.candles)-1].close, self.dataset.candles[len(self.dataset.candles)-1].timestamp)
                        self.closeShort(trade)
        
        for trade in self.trades:
            if not trade.isClosed():
                closingRun()

    def applySimpleTrendScoreStrategy(self, activationScore, maxOpen, closingAge):
        if len(self.trades) == 0:
            permBull = []
            permBear = []

            for candle in self.dataset.candles:
                currentPrice = candle.close
                currentTime = candle.timestamp
                change = candle.getPercentageChange()
                
                def updateTrendScore():
                    if candle.bullish:
                        if change > 0 and change < 1:
                            self.bullBias += 1
                        else:
                            for refChange in range(1, 21):
                                if change <= refChange:
                                    permBull.append(refChange)
                                    break
                                self.bullBias += 1
                    else:
                        if change <= 0 and change > -1:
                            self.bearBias += 1
                        else:
                            for refChange in range(-1, -21):
                                if change >= refChange:
                                    print(refChange)
                                    permBear.append(refChange)
                                    break
                                self.bearBias += 1
                
                def resetTrendScore():
                    if self.bullBias > activationScore*2:
                        self.bullBias = activationScore/2
                    if self.bearBias > activationScore*2:
                        self.bearBias = activationScore/2

                def tradeOpener():
                    if self.currentTradesOpen() <= maxOpen:
                        if self.bullBias > activationScore:
                            self.openLong(currentTime, currentPrice)
                        if self.bearBias > activationScore:
                            self.openShort(currentTime, currentPrice)
                    else: self.closeBestTradeUnderTP(currentPrice, currentTime)
                
                resetTrendScore()
                updateTrendScore()
                tradeOpener()
                self.TPRound(currentPrice, currentTime)
                self.SLRound(currentPrice, currentTime, closingAge)
                
            self.closeRemainingTrades() #realy making sure

        else: raise RuntimeError("This strategy has already been applied to the dataset!")

        self.simpleStrat = (activationScore, maxOpen, closingAge)
        self.getStrategyPNL()

    def applyComplexTrendScoreStrategy(self, strategy):
        momentumBias = 0
        recencyBias = 0
        priceBias = 0
        macroBias = 0
        trendScore = None
        for x in len(self.dataset.candles):
            candle = self.dataset.candles[x]
            currentPrice = self.dataset.candles[x].close
            for movAv in candle.getAllSMAs():
                if movAv != 0.0:
                    if currentPrice < movAv:
                        distance = ((currentPrice/movAv)-1)*-1

    def applyHeikenAshiStrategy(self):
        pass

    def applyRenkoStrategy(self):
        pass
    
    def getProfitableTrades(self):
        profitable = 0
        for trade in self.trades:
            if trade.isClosed():
                if trade.rawPNL > 0:
                    profitable += 1
        return profitable

    def getStrategyPNL(self):
        self.finalUSD = self.positionUSD + (self.positionCOIN*self.dataset.candles[len(self.dataset.candles)-1].close) #to adjust sip sip sleeping
        self.totalFeesUSD = (len(self.trades)*2*self.FEES_VALUE)*self.tradesSizeUSD
        self.finalUSD -= self.totalFeesUSD
        if self.finalUSD > self.initialUSD:
            self.botPNL = ((self.initialUSD/self.finalUSD)-1)*-100
            return ((self.initialUSD/self.finalUSD)-1)*-100
        else:
            self.botPNL = ((self.finalUSD/self.initialUSD)-1)*100
            return ((self.finalUSD/self.initialUSD)-1)*100

    def __str__(self):
        if len(self.trades) > 0:
            try:                
                str = {
                    "content" : f"Backtest results overivew (Timeframe: {self.dataset.timeframe}, Market: {self.dataset.market}):\n"
                    + f"Starting USD equivalent: {self.initialUSD} $ --> ({std_2rounding(self.initialUSD*self.startingAllocation)} $, {std_8rounding(self.initialCOIN*(1-self.startingAllocation))} COIN)\n"
                    + f"Final USD equivalent: {std_2rounding(self.finalUSD)} $ --> ({std_2rounding(self.positionUSD)} $, {std_8rounding(self.positionCOIN)} COIN), Strategy PNL: {std_4rounding(self.getStrategyPNL())} %\n"
                    + f"Total trades: {len(self.trades)} of which {self.getProfitableTrades()} were profitable, Failed to open {len(self.failedTrades)} trades, Failed to close {self.failedTP+self.failedSL} times\n"
                    + f"Trades size: {self.tradesSizeUSD} $ ({std_8rounding(self.tradesSizeCOIN)} COIN), Take profit value used: {self.tpValue} %, Total fees paid: {self.totalFeesUSD} $\n"
                    + f"Simple strategy tuple: [long/short trade activation score: {self.simpleStrat[0]}, max trades open at the same time: {self.simpleStrat[1]}, max time open for each position: {self.simpleStrat[2]} candles]\n"
                }
            except ValueError:
                pass
            return str.get("content")
        else: return "This strategy has 0 trades attached\n"

#OPTIMIZER
class BacktestStrategyIterator():

    initialUSDs = (0, 1200, 200)
    tradesSizesUSD = (0, 220, 20)
    startingAllocations = (0, 125, 25) #0 means no USD, 100 means all USD
    tpValues = (0, 50, 10)

    def __init__(self, loadedDataset = BackTestLoader):
        self.loadedDataset = loadedDataset
        self.bots: List[str] = []
        self.botsPNLs: List[float] = []
        self.best = None
        self.winningBots = 0
        self.losingBots = 0
        self.totalPossibleConfigs = 0
        self.validConfigs = 0
        self.invalidConfigs = 0
        self.failedConfigs = 0

    def validPreset(self, initialUSD, tradesSizeUSD, startingAllocation, tpValue):
        return initialUSD >= 10 and 0 <= startingAllocation <= 1 and tpValue > 0 and (initialUSD*startingAllocation) > tradesSizeUSD

    def randomizeSimpleStrategyParams(self, maxScore, maxMaxOpen, maxClosingAge): #very heavy method, range step between input parameters is 1
        if self.loadedDataset.ready:
            runner =  BackTestRunner(self.loadedDataset.dataset, self.loadedDataset.dataset.timeframe, self.loadedDataset.dataset.market, initialUSD = 5000,
                                    tradesSizeUSD = 500, startingAllocation = 0.5, tpValue = 10)
            validBots = []
            pnls = []
            for score in range(10, maxScore+1):
                for open in range(10, maxMaxOpen+1):
                    for age in range(30, maxClosingAge+1):
                        try:
                            self.totalPossibleConfigs += 1
                            runner.runSimpleStrategyBacktest(activationScore = score, maxOpen = open, closingAge = age)
                            validBots.append(runner.bot.__str__())
                            pnls.append(runner.bot.botPNL)
                            runner.bot.resetBot()
                            self.validConfigs += 1
                        except RuntimeError:
                            self.failedConfigs += 1
                            runner.bot.resetBot()
                            continue
                        except AttributeError:
                            self.failedConfigs += 1
                            runner.bot.resetBot()
                            continue

            self.bots.extend(validBots)
            self.botsPNLs.extend(pnls)
            self.validConfigs = len(self.bots)
        else: raise AttributeError("Check the loaded dataset!")

        #BESTIA NERA
        #  for initialUSD in range(self.initialUSDs[0], self.initialUSDs[1], self.initialUSDs[2]):
        #        for tradesSize in range(self.tradesSizesUSD[0], self.tradesSizesUSD[1], self.tradesSizesUSD[2]):
        #            for allocation in range(self.startingAllocations[0], self.startingAllocations[1], self.startingAllocations[2]):
        #                for tp in range(self.tpValues[0], self.tpValues[1], self.tpValues[2]):
        #                    self.totalPossibleConfigs += 1
        #                    if self.validPreset(initialUSD, tradesSize, std_2rounding(allocation/100), tp):
        #                        try:
        #                            runner.setNewBotParameters(initialUSD = initialUSD, tradesSizeUSD = tradesSize, startingAllocation = std_2rounding(allocation/100), tpValue = tp) 
        #remember invalid configs!

    def removeBotsWithNegativePNL(self):
        totalBots = len(self.bots)
        for bot in self.bots:
            if bot.find("Strategy PNL: -") != -1:
                self.bots.remove(bot)
        self.winningBots = len(self.bots)
        self.losingBots = totalBots - self.winningBots

    def setBestBotByPNL(self):
        bestPNL = max(self.botsPNLs)
        for bot in self.bots:
            if bot.find(f"Strategy PNL: {std_4rounding(bestPNL)} %") != -1:
                self.best = bot
                break

    def __str__(self):
        if len(self.bots) != 0:
            str = { "content" : f"{self.loadedDataset.dataset.__str__()} \n\nTotal tried configuration[{self.validConfigs}, {self.winningBots} with positive PNL and {self.losingBots} with negative PNL]"
                   + f"\nOptimal bot configuration for this dataset:{self.best}" }
            return str.get("content")
        else: return "No strategy iterated!"
            
#STRATEGIES
class ComplexStrategy():
    pass





    
    

    
    
    