from dhanhq import DhanContext, HistoricalData
import pandas as pd
from datetime import datetime, timedelta
import getpass

CLIENT_ID = input("Enter Dhan Client ID: ")
ACCESS_TOKEN = getpass.getpass("Enter Dhan Access Token: ")

# Nifty 50 index details for Dhan
SECURITY_ID = "13"
EXCHANGE_SEGMENT = "IDX_I"
INSTRUMENT_TYPE = "INDEX"

INTERVAL = 15
LOT_SIZE = int(input("Enter Nifty lot size / quantity: "))

ctx = DhanContext(CLIENT_ID, ACCESS_TOKEN)
historical = HistoricalData(ctx)

all_dfs = []

end_date = datetime.today()

for i in range(5):  # 5 x 90 days = approx 450 days
    start_date = end_date - timedelta(days=90)

    print(f"Downloading {start_date.date()} to {end_date.date()}")

    data = historical.intraday_minute_data(
        security_id=SECURITY_ID,
        exchange_segment=EXCHANGE_SEGMENT,
        instrument_type=INSTRUMENT_TYPE,
        from_date=start_date.strftime("%Y-%m-%d"),
        to_date=end_date.strftime("%Y-%m-%d"),
        interval=INTERVAL
    )

    if data.get("status") == "success":
        df = pd.DataFrame(data["data"])

        if not df.empty:
            all_dfs.append(df)
            print("Rows:", len(df))
        else:
            print("No data received")
    else:
        print("Error:", data)

    end_date = start_date

if not all_dfs:
    print("No data downloaded. Check token, security_id, or Dhan API response.")
    exit()

full_df = pd.concat(all_dfs, ignore_index=True)

full_df["timestamp"] = pd.to_datetime(
    full_df["timestamp"],
    unit="s",
    utc=True
).dt.tz_convert("Asia/Kolkata")

full_df = full_df.sort_values("timestamp").reset_index(drop=True)

print("TOTAL ROWS:", len(full_df))
print(full_df["timestamp"].head())

full_df["EMA9"] = full_df["close"].ewm(span=9, adjust=False).mean()
full_df["EMA21"] = full_df["close"].ewm(span=21, adjust=False).mean()
full_df["EMA50"] = full_df["close"].ewm(span=50, adjust=False).mean()
full_df["VOL20"] = full_df["volume"].rolling(20).mean()

long_signals = (
    (full_df["EMA9"] > full_df["EMA21"]) &
    (full_df["EMA9"].shift(1) <= full_df["EMA21"].shift(1))
)

short_signals = (
    (full_df["EMA9"] < full_df["EMA21"]) &
    (full_df["EMA9"].shift(1) >= full_df["EMA21"].shift(1))
)

print("Long signals:", int(long_signals.sum()))
print("Short signals:", int(short_signals.sum()))

trades = []

for i in range(1, len(full_df) - 1):
    trade_time = full_df.iloc[i]["timestamp"].time()

    if not (
        trade_time >= pd.Timestamp("09:15").time()
        and trade_time <= pd.Timestamp("15:15").time()
    ):
        continue

    # LONG ENTRY
    if (
        long_signals.iloc[i]
        and full_df.iloc[i]["EMA21"] > full_df.iloc[i]["EMA50"]
        and full_df.iloc[i]["close"] > full_df.iloc[i]["EMA50"]
        and full_df.iloc[i]["close"] > full_df.iloc[i]["open"]
        and full_df.iloc[i]["volume"] > full_df.iloc[i]["VOL20"]
    ):
        entry_price = full_df.iloc[i + 1]["open"]

        target = entry_price * 1.004
        stoploss = entry_price * 0.998

        for j in range(i + 1, len(full_df)):
            if full_df.iloc[j]["low"] <= stoploss:
                pnl = (stoploss - entry_price) * LOT_SIZE
                trades.append(pnl)
                break

            if full_df.iloc[j]["high"] >= target:
                pnl = (target - entry_price) * LOT_SIZE
                trades.append(pnl)
                break

wins = [x for x in trades if x > 0]
losses = [x for x in trades if x < 0]

print()
print("========== NIFTY 50 RESULTS ==========")
print("Trades:", len(trades))
print("Wins:", len(wins))
print("Losses:", len(losses))

if trades:
    print("Win Rate:", round(len(wins) / len(trades) * 100, 2), "%")
else:
    print("Win Rate: 0 %")

if wins:
    print("Average Win:", round(sum(wins) / len(wins), 2))
else:
    print("Average Win: 0")

if losses:
    print("Average Loss:", round(abs(sum(losses)) / len(losses), 2))
else:
    print("Average Loss: 0")

print("Net Profit:", round(sum(trades), 2))