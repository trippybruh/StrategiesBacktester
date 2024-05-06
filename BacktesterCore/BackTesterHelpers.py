import logging, numpy, datetime, os, pickle, jsonpickle

# logger/directory handler
WORKSPACE_BASE_DIR = os.path.dirname(__file__)
DATA_GROUPER_DIR = WORKSPACE_BASE_DIR # +"yearlyDataGrouper\\"


def loggingToFile(filepath):
    logging.basicConfig(filename=filepath, filemode="a", level=logging.INFO, format=f"Log file created on {datetime.datetime.now()}"+"\n%(message)s")


def loggingFileFormat(timeframe, market, strategy, timestamp):
    basedir = WORKSPACE_BASE_DIR + timeframe + f"\\{market}\\backtests\\"
    return f"{basedir}{strategy}\\{timestamp}.txt"


def logData(data):
    logging.info(data.__str__())


def candlesDataFilepath(timeframe, market, year):
    return f"{WORKSPACE_BASE_DIR}{timeframe}\\{market}\\{year}.csv"


def createYearlyData(fileNameSrc, year):
    if fileNameSrc != None and year >= 2010:
        if fileNameSrc.find('-01') != -1:
            fileNameSrc = DATA_GROUPER_DIR + fileNameSrc
            fileNameDst = DATA_GROUPER_DIR + f"{year}.csv"
            nextSrc = fileNameSrc
            toDump = fileNameSrc
            with open(fileNameDst, 'x') as dst:
                for x in range(1, 12):
                    if x < 9:
                        with open(nextSrc, 'r') as src:
                            for line in src:
                                dst.write(line)
                            nextSrc = nextSrc.replace(f"-0{x}",f"-0{x+1}")
                    elif x == 9: 
                        with open(nextSrc, 'r') as src:
                            for line in src:
                                dst.write(line)
                            nextSrc = nextSrc.replace(f"-0{x}",f"-{x+1}")
                    else:
                        with open(nextSrc, 'r') as src:
                            for line in src:
                                dst.write(line)
                            nextSrc = nextSrc.replace(f"-{x}",f"-{x+1}")

                with open(nextSrc, 'r') as src:
                    for line in src:
                        dst.write(line)
                src.close(), dst.close()

            for x in range(1, 13):
                if x < 9:
                    os.remove(toDump)
                    toDump = toDump.replace(f"-0{x}",f"-0{x+1}")
                elif x == 9:
                    os.remove(toDump)
                    toDump = toDump.replace(f"-0{x}",f"-{x+1}")
                else:
                    os.remove(toDump)
                    toDump = toDump.replace(f"-{x}",f"-{x+1}")

        else: raise FileNotFoundError(f"file source error!{fileNameSrc}")
    else: raise AttributeError("Input correct source and year!")


# numeric
def std_2rounding(value):
    return numpy.round(value, 2)


def std_4rounding(value):
    return numpy.round(value, 4)


def std_8rounding(value):
    return numpy.round(value, 8)


def timestampToDate(timestamp):
    return datetime.datetime.fromtimestamp(int(timestamp/1000))

# backtest default inputs


DEFAULT_INITIAL = 5000
DEFAULT_TRADES_SIZE_RATIO = 0.0166666
DEFAULT_TRADES_SIZE = std_2rounding(DEFAULT_INITIAL*DEFAULT_TRADES_SIZE_RATIO)
ALLOCATION_50_50 = 0.5
MINIMAL_TP = 1
FEES_VALUE = 0.001 # % factor

# readyDatasets
DAILY_DATASETS_DIR = WORKSPACE_BASE_DIR + "1D\\defaultDatasets\\"
HOURLY_DATASETS_DIR = WORKSPACE_BASE_DIR + "1h\\defaultDatasets\\"


def dailyDatasetNameFormat(market, startingYear, endingYear):
    return DAILY_DATASETS_DIR + f"{market}_{startingYear}_{endingYear}"


def saveDatasetToFile(loadedDataset):
    if loadedDataset.ready:
        filePath = DAILY_DATASETS_DIR + f"{loadedDataset.dataset.market}_{loadedDataset.startingYear}_{loadedDataset.endingYear}"
        with open(filePath, 'wb') as file:
            pickle.dump(loadedDataset, file)
            file.close()
    else: raise AttributeError("Cannot save unloaded dataset!")


def getRawDatasetFromFileForOptimization(filePath):
    with open(filePath, 'rb') as file:
        dataset = pickle.load(file)
        file.close()
    return dataset


def getRawDatasetFromFileForRunner(filePath):
    return getRawDatasetFromFileForOptimization(filePath).dataset


def getJsonDatasetFromFile(filePath):
    return jsonpickle.decode(getRawDatasetFromFileForOptimization(filePath))

