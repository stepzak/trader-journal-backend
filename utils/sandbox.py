import talib
import yfinance
a = yfinance.download("XRP-USD")
df = talib.CDL3BLACKCROWS(
    a["Open"],
    a["High"],
    a["Close"],
    a["Low"],
)
print(df[df != 0])