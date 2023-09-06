import logging, numpy, datetime

#logger/directory handler
def loggingToFile(filepath):
    logging.basicConfig(filename=filepath, filemode="a", level=logging.INFO, format=f"Log file created on {datetime.datetime.now()}"+"\n%(message)s")

def loggingFilepath(timeframe, market, strategy):
    basedir = f"C:\\Users\\TRIPPYBRUH\\Desktop\\stuff\\BinanceAPI project\\MOONSHOTTER\\{timeframe}\\{market}\\backtests\\"
    return f"{basedir}{strategy}\\{int(datetime.datetime.now().timestamp())}.txt"

def logData(data):
    logging.info(data.__str__())

def candlesDataFilepath(timeframe, market, year):
    #can be generalized with base filepath
    return f"C:\\Users\\TRIPPYBRUH\\Desktop\\stuff\\BinanceAPI project\\MOONSHOTTER\\{timeframe}\\{market}\\{year}.csv"

def createYearlyData(startingSrc = str, filepathDst = str):
    if startingSrc.find('-01') != -1:
        nextSrc = startingSrc
        with open(filepathDst, 'w') as dst:
            for x in range(1, 12):
                print(nextSrc)
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

#numeric
def std_2rounding(value):
    return numpy.round(value, 2)

def std_4rounding(value):
    return numpy.round(value, 4)

def std_8rounding(value):
    return numpy.round(value, 8)

def timestampToDate(timestamp):
    return datetime.datetime.fromtimestamp(int(timestamp/1000))

#data strings
# str = { "content" : f"" 
#         + f""
#         + f""
#         + f""
#         + f""
#         + f""
#         + f""
#         + f""
# }