from config.settings import settings

try:
    from fyers_apiv3.FyersWebsocket.tbt_ws import FyersTbtSocket, SubscriptionModes
    HAS_TBT = True
except ImportError:
    HAS_TBT = False

def on_depth_update(ticker, message):
    """
    Handles live Level-2 Tick-By-Tick market depth updates.
    Feeds bid-ask depth into the Anil Babu Trades execution microstructure engine.
    """
    bids = message.get("bids", [])
    asks = message.get("asks", [])
    best_bid = bids[0]["price"] if bids else 0.0
    best_ask = asks[0]["price"] if asks else 0.0
    spread = round(best_ask - best_bid, 2) if best_ask and best_bid else 0.0

    print(f"📊 [TBT DEPTH] {ticker} | Bid: ₹{best_bid} | Ask: ₹{best_ask} | Spread: ₹{spread} | Volume: {message.get('vol_traded_today', 0)}")

def onerror_message(message):
    print("⚠️ Fyers TBT Server Error:", message)

def onerror(message):
    print("❌ Fyers TBT Socket Error:", message)

def onclose(message):
    print("🔌 Fyers TBT Connection Closed:", message)

def run_tbt_stream(symbols=None):
    """
    Subscribes to ultra-low latency Tick-By-Tick depth streams for Nifty & BankNifty futures.
    """
    if not HAS_TBT:
        print("⚠️ fyers_apiv3 library not found. Please install with: pip install fyers-apiv3")
        return

    if not settings.FYERS_ACCESS_TOKEN:
        print("⚠️ No FYERS_ACCESS_TOKEN found in .env. Run `python scripts/fyers_auth_login.py` first to generate your token.")
        return

    symbols = symbols or ["NSE:NIFTY26AUGFUT", "NSE:BANKNIFTY26AUGFUT"]
    channel_no = "1"
    token_str = f"{settings.FYERS_APP_ID}:{settings.FYERS_ACCESS_TOKEN}"

    def onopen():
        print(f"✅ Fyers TBT Connected! Subscribing to: {symbols} on Channel {channel_no}")
        fyers.subscribe(symbol_tickers=symbols, channelNo=channel_no, mode=SubscriptionModes.DEPTH)
        fyers.switchChannel(resume_channels=[channel_no], pause_channels=[])
        fyers.keep_running()

    fyers = FyersTbtSocket(
        access_token=token_str,
        write_to_file=False,
        log_path="",
        on_open=onopen,
        on_close=onclose,
        on_error=onerror,
        on_depth_update=on_depth_update,
        on_error_message=onerror_message
    )

    print("🚀 Starting Fyers TBT WebSocket Depth Engine...")
    fyers.connect()

if __name__ == "__main__":
    run_tbt_stream()
