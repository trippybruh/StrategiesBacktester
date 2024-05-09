from BacktesterCore.BackTester import *
from BacktesterCore.BackTesterHelpers import *

if __name__ == "__main__":
    x = 0
    if x == 0: 
        runner = BackTestRunner(getRawDatasetFromFileForOptimization(dailyDatasetNameFormat("BTCUSDT", 2018, 2023)), "1D", "BTCUSDT", initialUSD = DEFAULT_INITIAL,
                                tradesSizeUSD = DEFAULT_TRADES_SIZE, startingAllocation = ALLOCATION_50_50, tpValue = 21, plottable = True, adaptiveTradesSize = False)
        runner.runSimpleStrategyBacktest(activationScore = 10, maxOpen = 15, closingAge = 15)
        dataPlotter = BacktestGraph(runner)
        dataPlotter.loadPerformanceOnGraph(True)
        dataPlotter.showBacktest()

  





        