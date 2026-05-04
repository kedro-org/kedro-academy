import json
import os
import yfinance as yf
from cacheout import Cache

# Default cache size
CACHE_SIZE = 500
DEFAULT_TTL = 300  # seconds


def init_context(context):
    """
    Initialize Nuclio context with a cache (LRU + TTL)
    """
    ttl = int(os.environ.get("CACHE_TTL_SECONDS", DEFAULT_TTL))
    context.logger.info(f"Initializing stock cache (size={CACHE_SIZE}, ttl={ttl}s)")

    # LRU cache with TTL
    context.stock_cache = Cache(maxsize=CACHE_SIZE, ttl=ttl)


def handler(context, event):
    """
    Nuclio handler: fetch stock price and cache the last 500 requests with TTL
    """
    try:
        # Get stock symbol from JSON payload or query param
        data = event.body.decode("utf-8")
        if data:
            payload = json.loads(data)
            symbol = payload.get("symbol", "").upper()
        else:
            symbol = event.params.get("symbol", "").upper()

        if not symbol:
            return context.Response(
                body=json.dumps({"error": "No stock symbol provided"}),
                content_type="application/json",
                status_code=400,
            )

        # Check cache
        price = context.stock_cache.get(symbol)
        if price is not None:
            return context.Response(
                body=json.dumps({"symbol": symbol, "price": price, "cached": True}),
                content_type="application/json",
                status_code=200,
            )

        # Fetch from yfinance
        stock = yf.Ticker(symbol)
        info = stock.info
        price = info.get("regularMarketPrice")

        if price is None:
            return context.Response(
                body=json.dumps({"error": f"Could not fetch price for {symbol}"}),
                content_type="application/json",
                status_code=404,
            )

        # Store in cache
        context.stock_cache.set(symbol, price)

        return context.Response(
            body=json.dumps({"symbol": symbol, "price": price}),
            content_type="application/json",
            status_code=200,
        )

    except Exception as e:
        return context.Response(
            body=json.dumps({"error": str(e)}),
            content_type="application/json",
            status_code=500,
        )
