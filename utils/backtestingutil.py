import datetime
import uuid
from ast import literal_eval
from typing import Tuple, Literal, Dict, List
# import pandas_ta
import pandas as pd
import yfinance
from backtesting import Backtest, Strategy
import talib as ta
from backtesting.lib import crossover
from backtesting.test import SMA, GOOG

params = [
    {"indicator": "rsi", "kwargs": {"period": 14, "buy_rsi": 70, "sell_rsi": 30}, "positive_signal": 2,
     "negative_signal": -2},
    {"indicator": "sma", "kwargs": {"ma1_period": 10, "ma2_period": 20}, "positive_signal": 2,
     "negative_signal": -2},
    {"indicator": "aroon", "kwargs": {"period": 14, "buy_on": 100, "sell_on": -100}, "positive_signal": 2,
     "negative_signal": -2},
    {"indicator": "ema", "kwargs": {"period": 14, "buy_on": "higher", "sell_on": "lower"}, "positive_signal": 2,
     "negative_signal": -2},
    {"indicator": "cdl3blackcrows", "kwargs": {"sell_on": -100, "buy_on": 100}, "positive_signal": 2,
     "negative_signal": -2},
    {"indicator": "macd", "kwargs": {}, "positive_signal": 2, "negative_signal": -2},
]
# help(ta.AROON)

params_logical = [
    {"indicator": "rsi",
     "kwargs": {"period": 14},
     "logical": [
         {
             "signal": 2,
             "signal_false": 0,
             "expressions": [
                 {"tie_to": "number", "expression": ">=", "value": 70}
             ]
         },
         {
             "signal": -2,
             "expressions": [{"tie_to": "number", "expression": "<=", "value": 30}]
         },
     ]
     },
    {
        "indicator": "sma",
        "kwargs": {"ma1_period": 10, "ma2_period": 20},
        "logical": [
            {
                "signal": 2,
                "expressions": [
                    {"tie_to": "ma2", "expression": "crossover"}
                ]
            },
            {
                "signal": -2,
                "expressions": [
                    {"tie_to": "ma1", "expression": "crossover"}
                ]
            }
        ]
    },
]


def test_run(data, strategyName, indicators: List[Dict] = [{}], tp=0.03, sl=0.02, sell_size=0.02, buy_size=0.02,
             scalping: bool = False, cash=1000, margin=1 / 10, commission=0.0007, buy_signal=0.1,
             sell_signal=-0.1) -> Backtest:
    class BasicStrategy(Strategy):
        def init(self):
            for strat in indicators:
                if strat["indicator"] == "rsi":
                    print(strat.get("kwargs", {}).get("period", 14))
                    self.rsi = self.I(ta.RSI, self.data.Close, int(strat.get("kwargs", {}).get("period", 14)))
                elif strat["indicator"] == "sma":
                    #print(strat.get("kwargs", {}).get("ma1_period", 10))
                    #print(strat.get("kwargs", {}).get("ma2_period", 20))
                    self.ma1 = self.I(SMA, self.data.Close, strat.get("kwargs", {}).get("ma1_period", 10))
                    self.ma2 = self.I(SMA, self.data.Close, strat.get("kwargs", {}).get("ma2_period", 20))
                elif strat["indicator"] == "macd":
                    self.macd = self.I(lambda x: ta.MACD(x)[0], self.data.Close)
                    self.macd_signal = self.I(lambda x: ta.MACD(x)[1], self.data.Close)
                elif strat["indicator"] == "aroon":
                    self.aroon = self.I(ta.AROON, self.data.Low, self.data.High)
                elif strat["indicator"] == "cdl3blackcrows":
                    print(self.data.Close.__array__())
                    self.cdl3blackcrows = self.I(ta.CDL3BLACKCROWS, self.data.Open, self.data.High, self.data.Close, self.data.Low,)


                elif strat["indicator"] == "ema":
                    self.ema = self.I(ta.EMA, self.data.Close, timeperiod=strat["kwargs"].get("period", 14))

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
            # print(self.aroon[-1][-1])
            if 100 <= self.aroon[-1][-1]:
                return positive_signal
            elif -100 >= self.aroon[-1][-1]:
                return negative_signal
            return 0

        def check_3blackcrows(self, arg, price, kwargs, positive_signal, negative_signal):

            if 100 == self.cdl3blackcrows[-1]:
                return positive_signal
            elif -100 == self.cdl3blackcrows[-1]:
                return negative_signal
            return 0

        def check_ema(self, arg, price, kwargs, positive_signal, negative_signal):
            exp_enum = {
                "higher": price > self.ema,
                "lower": price < self.ema
            }
            if price > self.ema:
                return positive_signal
            elif price < self.ema:
                return negative_signal
            return 0

        enum_strategy = {
            "rsi": check_rsi,
            "sma": check_sma,
            "macd": check_macd,
            "aroon": check_aroon,
            "cdl3blackcrows": check_3blackcrows,
            "ema": check_ema
        }

        def get_rsi(self, operator):
            if operator != "crossover":
                return self.rsi[-1]
            return self.rsi

        def get_ma1(self, operator):
            return self.ma1

        def get_ma2(self, operator):
            return self.ma2

        def get_macd(self, operator):
            return self.macd

        def get_macd_signal(self, operator):
            return self.macd_signal

        def get_aroon(self, operator):
            if operator != "crossover":
                return self.aroon[-1][-1]
            else:
                return self.aroon[-1]

        def get_cdl3blackcrows(self, operator):
            return self.cdl3blackcrows[-1]

        def get_ema(self, operator):
            return self.ema

        def check_logical(self, logical: Dict, indicator: str):
            logical_enum = {
                "rsi": self.get_rsi,
                "ma1": self.get_ma1,
                "ma2": self.get_ma2,
                "macd": self.get_macd,
                "macd_signal": self.get_macd_signal,
                "aroon": self.get_aroon,
                "cdl3blackcrows": self.get_cdl3blackcrows,
                "ema": self.get_ema
            }
            for l in logical["expressions"]:
                tie_to = logical_enum.get(l["tie_to"], None) or l.get("value", 1)

                val_compare = indicator if indicator != "sma" else ""
                if val_compare == "":
                    val_compare = "ma1" if l["tie_to"] == "ma2" else "ma2"

                if not isinstance(tie_to, float) and not isinstance(tie_to, int):
                    tie_to = tie_to()

                val_compare = logical_enum[val_compare]()
                operator = l["expression"]
                if ">" in operator or "<" in operator or "=" in operator:
                    operator_enum = {
                        ">=": val_compare >= tie_to,
                        "<=": val_compare <= tie_to,
                        "<": val_compare < tie_to,
                        ">": val_compare < tie_to,
                        "=": val_compare == tie_to,
                        "==": val_compare == tie_to,
                    }

                else:

                    operator_enum = {
                        "crossover": crossover(val_compare, tie_to)
                    }
                if operator_enum[operator]:
                    continue
                return False
            return True

        def calculate_signal(self, indicator):
            logical = indicator.get("logical", [])
            signal = 0
            for logic in logical:
                res = self.check_logical(logic, indicator["indicator"])
                if res:
                    signal += logic["signal"]
                    continue
                else:
                    signal += logic.get("false_signal", 0)
            return signal

        def next(self):
            price = float(self.data.Close[-1])

            current_signal = 0
            """for indicator in indicators:
                signal = self.calculate_signal(indicator)
                current_signal += signal"""
            for indicator in indicators:

                res = self.enum_strategy[indicator["indicator"]](self, arg="", price=price, kwargs=indicator["kwargs"],
                                                                 positive_signal=indicator["positive_signal"],
                                                                 negative_signal=indicator["negative_signal"])
                current_signal += res

            if current_signal >= buy_signal:
                self.buy(size = buy_size, tp=(1 + tp) * price, sl=(1 - sl) * price)
            elif current_signal <= sell_signal:
                self.sell(size = sell_size, tp=(1 - tp) * price, sl=(1 + sl) * price)

    bt = Backtest(data, BasicStrategy, cash=cash, margin=margin, commission=commission)

    return bt


# print(yfinance.download("XRP-USD"))
if __name__ == "__main__":
    params = [
        {"indicator": "sma", "kwargs": {"ma1_period": 10, "ma2_period": 20}, "positive_signal": 2,
         "negative_signal": -2},
    ]
    run = test_run(GOOG,
                   buy_size=0.3, sell_size = 0.3,scalping=False, indicators=params, strategyName=str(uuid.uuid4()), cash=10000)
    print(run.run())
    print(run.plot(open_browser=False, filename="backtest_plots/" + str(uuid.uuid4())))
