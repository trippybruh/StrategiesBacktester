import unittest, numpy
from BacktesterCore.BackTester import *
from BacktesterCore.AlgoTradeHelpers import *

aTimeframe = "1D"
aMarket = "BTCUSDT"
aYear = 2021

class testBasicBacktestModules(unittest.TestCase):

    def setUp(self):
        self.aCandle = BacktestCandle(1, 10, 25, 5, 20)

        self.aPrice1 = 1
        self.aPrice2 = self.aPrice1*2
        self.aBuyTrade = BacktestTrade(1, True, 1, 5)
        self.aSellTrade = BacktestTrade(1, False, 1, 5)

        self.MAperiod = 20
        self.aDataset = BacktestDataset()
        self.aDataset.loadCandlesFromFile(candlesDataFilepath(aTimeframe, aMarket, aYear))
        
    def testDataLoading(self):
        self.assertIsInstance(self.aDataset.candles[0], BacktestCandle)
        self.assertIsInstance(self.aDataset.heikenAshiCandles[0], BacktestCandle)
        self.assertEqual(365, len(self.aDataset.candles))
        self.assertEqual(364, len(self.aDataset.heikenAshiCandles))
        # not implemented self.assertEqual(365, len(self.aDataset.renkoCandles))
        self.assertTrue(self.aDataset.checkLoadedDatesOrder())
        self.assertIsInstance(self.aDataset.getLoadedDates(False), numpy.ndarray)
        self.assertIsInstance(self.aDataset.getLoadedCloses(False), numpy.ndarray)

    def testAdditionalDataLoading(self): #moving averages and indicators
        self.assertListEqual([60930.1887, 60083.682, 51844.5514, 48122.9939, 45288.002, 0.0], self.aDataset.candles[300].getAllSMAs())
        self.assertListEqual([60718.778, 59061.8056, 54143.31, 49882.1375, 47898.2098, 0.0], self.aDataset.candles[300].getAllEMAs())
        self.assertEqual(len(BacktestCandle.SMAs_periods), len(self.aDataset.candles[300].getAllSMAs()))
        self.assertEqual(len(BacktestCandle.EMAs_periods), len(self.aDataset.candles[300].getAllEMAs()))
        self.assertEqual(365, len(self.aDataset.getLoadedSMA(20)))
        self.assertTrue(numpy.isnan(self.aDataset.getLoadedSMA(self.MAperiod)[self.MAperiod-2]))
        self.assertFalse(numpy.isnan(self.aDataset.getLoadedSMA(self.MAperiod)[self.MAperiod-1]))

    def testBuyTradeBehaviour(self):
        self.assertFalse(self.aBuyTrade.isClosed())
        self.assertEqual(self.aBuyTrade.getAgeInCandles((BacktestDataset.timeframes.get(aTimeframe))+1, aTimeframe), 1)
        self.assertEqual(100.0, self.aBuyTrade.getPNL(2))
        self.assertEqual(-50.0, self.aBuyTrade.getPNL(0.5))
        self.aBuyTrade.closeTrade(0.1, (BacktestDataset.timeframes.get(aTimeframe)/1000)+2)
        self.assertEqual(-90.0, self.aBuyTrade.rawPNL)
        self.assertTrue(self.aBuyTrade.isClosed())

    def testSellTradeBehaviour(self):
        self.assertFalse(self.aSellTrade.isClosed())
        self.assertEqual(self.aSellTrade.getAgeInCandles((BacktestDataset.timeframes.get(aTimeframe))+1, aTimeframe), 1)
        self.assertEqual(-50.0, self.aSellTrade.getPNL(2))
        self.assertEqual(100.0, self.aSellTrade.getPNL(0.5))
        self.aSellTrade.closeTrade(0.1, (BacktestDataset.timeframes.get(aTimeframe)/1000)+2)
        self.assertEqual(900.0, self.aSellTrade.rawPNL)
        self.assertTrue(self.aSellTrade.isClosed())

    def testLeveragedTradeBehaviour(self):
        levTrade = BacktestLeveragedTrade(1, True, 1, 5, 10)
        self.assertFalse(levTrade.isClosed())
        self.assertAlmostEqual(-10.0, levTrade.getPNL(0.99))
        self.assertAlmostEqual(200.0, levTrade.getPNL(1.2))
        self.assertFalse(levTrade.checkLiquidation(2, 0.93))
        levTrade.closeTrade(1.05, 2)
        self.assertTrue(levTrade.isClosed)
        del levTrade
        
    def testLeveragedTradeLiquidation(self):
        levTrade = BacktestLeveragedTrade(1, False, 1, 5, 10)
        self.assertFalse(levTrade.isClosed())
        self.assertAlmostEqual(1.085, levTrade.liqPrice)
        self.assertTrue(levTrade.checkLiquidation(2, 1.15))
        self.assertTrue(levTrade.isClosed())
        self.assertEqual(-100.0, levTrade.rawPNL)
        self.assertEqual(levTrade.liqPrice, levTrade.exitPrice)
        del levTrade

class testBacktestBot(unittest.TestCase):

    def setUp(self):
        self.aTimeframe = "1D"
        self.aMarket = "BTCUSDT"
        self.aYear = 2021
        self.empty = [0, 0, 0, 0, 0, 0]
        self.MAperiod = 20
        self.aDataset = BacktestDataset()
        self.aDataset.loadCandlesFromFile(candlesDataFilepath(self.aTimeframe, self.aMarket, self.aYear))

        self.aBot = BacktestBot(self.aDataset, DEFAULT_INITAL, DEFAULT_TRADES_SIZE, ALLOCATION_50_50, MINIMAL_TP*10, False, False)

class testBacktestLoading(unittest.TestCase):

    def setUp(self):
        self.loader = BackTestLoader()
        
    def testLoading(self):
        self.loader.loadYearlyBacktest(aTimeframe, aMarket, aYear, 2)

class testBacktestRunning(unittest.TestCase):

    def setUp(self):
        self.loader = BackTestLoader()
        self.loader.loadYearlyBacktest(aTimeframe, aMarket, aYear, 2)
        self.runner = BackTestRunner(self.loader.dataset, "1D", "BTCUSDT", initialUSD = DEFAULT_INITAL, tradesSizeUSD = DEFAULT_TRADES_SIZE, 
                                     startingAllocation = ALLOCATION_50_50, tpValue = 10, plottable = True, adaptiveTradesSize = False)

    def testRunning(self):
        self.runner.runSimpleStrategyBacktest(activationScore = 15, maxOpen = 30, closingAge = 20)

if __name__ == "__main__":
    unittest.main()