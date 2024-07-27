import datetime
import uuid
from typing import Tuple, Literal
#import pandas_ta
import pandas as pd
import yfinance
from backtesting import Backtest, Strategy
import talib as ta
from backtesting.lib import crossover
from backtesting.test import SMA

params = [
    {"indicator": "rsi", "kwargs": {"period": 14, "buy_rsi": 70, "sell_rsi": 30}, "positive_signal": 2, "negative_signal": -2},
    {"indicator": "sma", "kwargs": {"ma1_period": 10, "ma2_period": 20},  "positive_signal": 2, "negative_signal": -2},
    {"indicator": "aroon", "kwargs": {"period": 14, "buy_on": 100, "sell_on": -100},   "positive_signal": 2, "negative_signal": -2},
    {"indicator": "ema", "kwargs": {"period": 14, "buy_on": "higher", "sell_on": "lower"}, "positive_signal": 2, "negative_signal": -2},
    {"indicator": "cdl3balckcrows", "kwargs": {"sell_on": -100, "buy_on": 100}, "positive_signal": 2, "negative_signal": -2},
    {"indicator": "macd", "kwargs": {}, "positive_signal": 2, "negative_signal": -2},
]
#help(ta.AROON)


def test_run(data, strategyName, indicators=[], tp=0.03, sl=0.02, sell_size=0.02, buy_size=0.02,
             scalping: bool = False, cash=1000, margin=1 / 10, commission=0.0007, buy_signal = 0.1, sell_signal = -0.1) -> Backtest:
    class BasicStrategy(Strategy):
        def init(self):
            for strat in indicators:
                if strat["indicator"] == "rsi":
                    self.rsi = self.I(ta.RSI, self.data.Close, strat.get("kwargs", {}).get("period", 14))
                elif strat["indicator"]=="sma":
                    self.ma1 = self.I(SMA, self.data.Close, strat.get("kwargs", {}).get("ma1_period", 10))
                    self.ma2 = self.I(SMA, self.data.Close, strat.get("kwargs", {}).get("ma2_period", 20))
                elif strat["indicator"]=="macd":
                    self.macd = self.I(lambda x: ta.MACD(x)[0], self.data.Close)
                    self.macd_signal = self.I(lambda x: ta.MACD(x)[1], self.data.Close)
                elif strat["indicator"] == "aroon":
                    self.aroon = self.I(ta.AROON, self.data.Low, self.data.High)
                elif strat["indicator"] == "cdl3balckcrows":
                    self.cdl3blackcrows = self.I(ta.CDL3BLACKCROWS, self.data.Open, self.data.High,  self.data.Low, self.data.Close)
                elif strat["indicator"]=="ema":
                    self.ema = self.I(ta.EMA, self.data.Close, timeperiod = strat["kwargs"].get("period", 14))


        def __str__(self):
            return strategyName

        def check_rsi(self, arg, price, kwargs, positive_signal, negative_signal):
            if not self.position and self.rsi[-2] < kwargs.get("buy_rsi", 70):
                # self.buy(size=kwargs.get("buy_size", 0.02), tp=(1 + tp) * price, sl=(1 - sl) * price)
                return positive_signal
            elif not self.position and self.rsi[-2] > kwargs.get("sell_rsi", 30):
                # self.sell(size=kwargs.get("sell_size", 0.02), tp=(1 - tp) * price, sl=(1 + sl) * price)
                return negative_signal
            return 0

        def check_sma(self, arg, price, kwargs, positive_signal, negative_signal):
            if crossover(self.ma1, self.ma2):
                return positive_signal
            elif crossover(self.ma2, self.ma1):
                return negative_signal
            return 0

        def check_macd(self, arg, price, kwargs, positive_signal, negative_signal):
            if crossover(self.macd, self.macd_signal):
                return positive_signal
            elif crossover(self.macd_signal, self.macd):
                return negative_signal
            return 0

        def check_aroon(self, arg, price, kwargs, positive_signal, negative_signal):
            #print(self.aroon[-1][-1])
            if kwargs["buy_on"]<=self.aroon[-1][-1]:
                return positive_signal
            elif kwargs["sell_on"]>=self.aroon[-1][-1]:
                return negative_signal
            return 0

        def check_3blackcrows(self, arg, price, kwargs, positive_signal, negative_signal):
            print(self.cdl3blackcrows)
            if kwargs["buy_on"]==self.cdl3blackcrows[-2]:
                return positive_signal
            elif kwargs["sell_on"]==self.cdl3blackcrows[-2]:
                return negative_signal
            return 0

        def check_ema(self, arg, price, kwargs, positive_signal, negative_signal):
            exp_enum = {
                "higher": price>self.ema,
                "lower": price<self.ema
            }
            if exp_enum[kwargs["buy_on"]]:
                return positive_signal
            elif exp_enum[kwargs["sell_on"]]:
                return negative_signal
            return 0



        enum_strategy = {
            "rsi": check_rsi,
            "sma": check_sma,
            "macd": check_macd,
            "aroon": check_aroon,
            "cdl3balckcrows": check_3blackcrows,
            "ema": check_ema
        }

        def next(self):
            price = float(self.data.Close[-1])

            current_signal = 0
            for indicator in indicators:
                res = self.enum_strategy[indicator["indicator"]](self, arg="", price = price, kwargs = indicator["kwargs"],
                                                                 positive_signal = indicator["positive_signal"],
                                                                 negative_signal = indicator["negative_signal"])
                if res == 0:
                    res = current_signal
                if res == current_signal or current_signal == 0:
                    current_signal += res



            if current_signal >= buy_signal:
                self.buy(size=buy_size, tp=(1 + tp) * price, sl=(1 - sl) * price)
            elif current_signal <= sell_signal:
                self.sell(size=sell_size, tp=(1 - tp) * price, sl=(1 + sl) * price)

    bt = Backtest(data, BasicStrategy, cash=cash, margin=margin, commission=commission)

    return bt


# print(yfinance.download("XRP-USD"))
if __name__ == "__main__":
    run = test_run(yfinance.download("XRP-USD", start=datetime.datetime.now() - datetime.timedelta(days=365)),
                   buy_size=0.005, scalping=False, indicators=params, strategyName=str(uuid.uuid4()))
    print(run.run())
    print(run.plot(open_browser=False, filename="backtest_plots/" + str(uuid.uuid4())))
