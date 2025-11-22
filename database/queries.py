def get_historical_prices_query():
    """Get daily closing prices for multiple symbols over a date range"""
    return """
        SELECT symbol, date, close
        FROM public.stock_data
        WHERE symbol = ANY(%s)
        AND date >= %s
        AND date <= %s
        ORDER BY symbol, date
    """

def get_latest_price_query():
    """Get the most recent closing price for a symbol"""
    return """
        SELECT symbol, date, close
        FROM public.stock_data
        WHERE symbol = %s
        ORDER BY date DESC
        LIMIT 1
    """

def get_nifty50_data_query():
    """Get Nifty 50 index data for beta calculation"""
    return """
        SELECT date, close
        FROM public.stock_data
        WHERE symbol = '^NSEI'
        AND date >= %s
        AND date <= %s
        ORDER BY date
    """

def check_symbols_exist_query():
    """Check if symbols exist in database"""
    return """
        SELECT DISTINCT symbol
        FROM public.stock_data
        WHERE symbol = ANY(%s)
    """
