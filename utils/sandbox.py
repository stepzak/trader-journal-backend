import datetime

import talib
import yfinance
a = yfinance.download("BTC-USD", start=datetime.datetime.now() - datetime.timedelta(days=365*8))
print(type(a["Close"].values))
df = talib.CDL3BLACKCROWS(
    a["Open"].values,
    a["High"].values,
    a["Close"].values,
    a["Low"].values,
)
print(df[df != 0])

#print(talib.VAR(a["Close"]))