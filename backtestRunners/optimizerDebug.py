from BacktesterCore import BackTester as BT
from BacktesterCore import BackTesterHelpers as BTH


if __name__ == "__main__":
    x = 0
    if x == 0: 
        optimizer = BT.BacktestStrategyOptimizer(BTH.getRawDatasetFromFileForOptimization(BTH.dailyDatasetNameFormat("BTCUSDT", 2020, 2021)))
        optimizer.randomizeSimpleStrategyParams(21, 15, 18, 15)
        print(optimizer.__str__()) #create logger 

    if x == 1:
        loader = BT.BackTestLoader()
        loader.loadYearlyBacktest("1D", "BTCUSDT", 2020, 1)
        BTH.saveDatasetToFile(loader)