"""
Fetch minute‐level equity returns with a client‐side rate‐limit window,
identify the top‐3 spike intervals (with counts), pick the best interval & day,
"""

import pandas as pd
import time
from datetime import datetime, timedelta
from polygon import RESTClient
import plotly.express as px
import plotly.graph_objects as go
from requests.exceptions import HTTPError, ConnectionError

# ————— Configuration —————
API_KEY           = ''
MARKET_OPEN       = "08:30"
MARKET_CLOSE      = "15:00"
MAX_CALLS_PER_MIN = 5    # calls per 60s window
# ——————————————————————————

client = RESTClient(API_KEY)

def fetch_data(ticker, start, end, duration):
    rows, calls, window_start = [], 0, time.time()
    current = start

    while current < end:
        if calls >= MAX_CALLS_PER_MIN:
            elapsed = time.time() - window_start
            wait = max(0, 60 - int(elapsed))
            for s in range(wait, 0, -1):
                print(f"\rWindow resets in {s:2d}s…", end="", flush=True)
                time.sleep(1)
            calls = 0
            window_start = time.time()
            print("\rWindow reset; resuming…     ")

        block_end = min(current + timedelta(days=59), end)
        frm, to = current.strftime("%Y-%m-%d"), block_end.strftime("%Y-%m-%d")
        print(f"\nFetching {ticker}: {frm} → {to}  (call {calls+1})")

        while True:
            try:
                aggs = client.get_aggs(ticker, duration, "minute", frm, to)
                break
            except HTTPError as e:
                if e.response.status_code == 429:
                    for s in range(60, 0, -1):
                        print(f"\r429 – retry in {s:2d}s…", end="", flush=True)
                        time.sleep(1)
                    calls = 0
                    window_start = time.time()
                    continue
                raise
            except ConnectionError:
                print("\nNetwork error; waiting 10s…")
                time.sleep(10)
                continue

        for bar in aggs:
            rows.append([bar.timestamp, bar.close])

        calls += 1
        current = block_end + timedelta(days=1)

    df = pd.DataFrame(rows, columns=["timestamp","close"])
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], unit="ms")
          .dt.tz_localize("UTC")
          .dt.tz_convert("America/Chicago")
    )
    df.set_index("timestamp", inplace=True)
    return df

def compute_top(df, duration):
    df = df.between_time(MARKET_OPEN, MARKET_CLOSE).copy()
    df["ret"]  = df["close"].pct_change().fillna(0)
    df["time"] = df.index.strftime("%H:%M")

    spikes = df[df["ret"].abs() >= 0.002]
    times  = spikes.index.time
    counts = spikes.groupby(times)["ret"].count()
    avgs   = spikes.groupby(times)["ret"].mean() * 100
    sds    = spikes.groupby(times)["ret"].std()  * 100

    top3    = avgs.nlargest(3)
    best_t  = top3.idxmax()
    best    = {
        "start": best_t.strftime("%H:%M"),
        "end":   (datetime.combine(datetime.today(), best_t)
                  + timedelta(minutes=duration)).time().strftime("%H:%M"),
        "mean":  avgs[best_t],
        "sd":    sds[best_t]
    }

    df["day"] = df.index.day_name()
    heat = (
        df.pivot_table("ret", index="day", columns="time", aggfunc="sum")
          .reindex(["Monday","Tuesday","Wednesday","Thursday","Friday"])
    )
    best_day = heat[best["start"]].idxmax()

    return heat, top3, counts, best, best_day


def plot_heatmap(heat, best):
    col = best["start"]
    z   = heat[[col]].values.tolist()
    x   = [col]
    y   = heat.index.tolist()
    fig = px.imshow(z, x=x, y=y,
                    labels={"x":"Start (CST)","y":"Day","color":"Return (%)"},
                    color_continuous_scale="RdYlGn", aspect="auto")
    fig.update_traces(hovertemplate="Day: %{y}<br>Return: %{z:.3f}%")
    fig.update_layout(title=f"{best['start']}–{best['end']} Agg Returns",
                      margin=dict(l=80, r=20, t=60, b=40))
    fig.show()

def plot_bar(best):
    fig = go.Figure(go.Bar(
        x=[best["start"]],
        y=[best["mean"]],
        error_y=dict(array=[best["sd"]], type="data")
    ))
    fig.update_layout(title=f"Return ±SD @ {best['start']}",
                      xaxis_title="Start (CST)",
                      yaxis_title="Return (%)",
                      margin=dict(l=60, r=20, t=60, b=40))
    fig.show()

def main():
    ticker    = input("Ticker symbol: ").upper().strip()
    qty, unit = input("Historical period (e.g. '2 years'): ").split()
    iq, iu    = input("Aggregation (e.g. '5 minutes'): ").split()
    qty, iq   = int(qty), int(iq)
    duration  = iq*60 if "hour" in iu.lower() else iq

    today = datetime.today()
    if "year" in unit:    start = today - timedelta(days=365*qty)
    elif "month" in unit: start = today - timedelta(days=30*qty)
    else:                  start = today - timedelta(days=qty)

    df = fetch_data(ticker, start, today, duration)
    heat, top3, counts, best, best_day = compute_top(df, duration)

    print("\nTop 3 intervals by avg return (with spike counts):")
    for t, avg in top3.items():
        end_t = (datetime.combine(datetime.today(), t)
                 + timedelta(minutes=duration)).time().strftime("%H:%M")
        print(f" {t.strftime('%H:%M')}-{end_t} → {avg:.2f}% over {counts[t]} spikes")

    print(f"\nBest: {best_day} {best['start']}-{best['end']}  Mean={best['mean']:.2f}%, SD={best['sd']:.2f}%\n")

    plot_heatmap(heat, best)
    plot_bar(best)

   
if __name__ == "__main__":
    main()
