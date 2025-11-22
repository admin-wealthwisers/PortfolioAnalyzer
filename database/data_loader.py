import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("Warning: yfinance not available, using mock data")

from database.db_connection import execute_query
from database.queries import (
    get_historical_prices_query,
    get_latest_price_query,
    get_nifty50_data_query,
    check_symbols_exist_query
)

# Import mock data if yfinance is unavailable
if not YFINANCE_AVAILABLE:
    from database.mock_data import MOCK_PRICES, generate_mock_historical_data, generate_mock_nifty_data

DEFAULT_LOOKBACK_DAYS = 252  # ~1 year of trading days


def get_current_price(symbol):
    """Get current price for a symbol, try PostgreSQL first, then yfinance/mock"""
    try:
        # Try PostgreSQL first
        result = execute_query(get_latest_price_query(), (symbol,), fetch_one=True)
        if result:
            return result['close']
    except Exception as e:
        print(f"PostgreSQL error for {symbol}: {e}")

    # Fallback to yfinance or mock
    if YFINANCE_AVAILABLE:
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return hist['Close'].iloc[-1]
        except Exception as e:
            print(f"yfinance error for {symbol}: {e}")
    else:
        # Use mock data
        price = MOCK_PRICES.get(symbol)
        if price:
            return price
        print(f"No mock data for {symbol}, using default")
        return 1000.0  # Default price

    return None


def get_historical_data(symbols, days=DEFAULT_LOOKBACK_DAYS):
    """
    Get historical OHLCV data for multiple symbols
    Returns: DataFrame with columns [symbol, date, close]
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days * 2)  # Extra buffer for weekends

    try:
        # Try PostgreSQL
        query = get_historical_prices_query()
        results = execute_query(query, (symbols, start_date, end_date))

        if results:
            df = pd.DataFrame(results)
            df['date'] = pd.to_datetime(df['date'])
            return df
    except Exception as e:
        print(f"PostgreSQL error: {e}")

    # Fallback to yfinance or mock
    all_data = []

    if YFINANCE_AVAILABLE:
        for symbol in symbols:
            try:
                ticker = yf.Ticker(f"{symbol}.NS")
                hist = ticker.history(period=f"{days * 2}d")
                if not hist.empty:
                    hist_df = pd.DataFrame({
                        'symbol': symbol,
                        'date': hist.index,
                        'close': hist['Close'].values
                    })
                    all_data.append(hist_df)
            except Exception as e:
                print(f"yfinance error for {symbol}: {e}")
    else:
        # Use mock data
        for symbol in symbols:
            mock_df = generate_mock_historical_data(symbol, days)
            all_data.append(mock_df)

    if all_data:
        return pd.concat(all_data, ignore_index=True)

    return pd.DataFrame(columns=['symbol', 'date', 'close'])


def get_nifty50_data(days=DEFAULT_LOOKBACK_DAYS):
    """Get Nifty 50 index data for beta calculation"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days * 2)

    try:
        # Try PostgreSQL
        results = execute_query(get_nifty50_data_query(), (start_date, end_date))
        if results:
            df = pd.DataFrame(results)
            df['date'] = pd.to_datetime(df['date'])
            return df
    except Exception as e:
        print(f"PostgreSQL error for Nifty: {e}")

    # Fallback to yfinance or mock
    if YFINANCE_AVAILABLE:
        try:
            ticker = yf.Ticker("^NSEI")
            hist = ticker.history(period=f"{days * 2}d")
            if not hist.empty:
                return pd.DataFrame({
                    'date': hist.index,
                    'close': hist['Close'].values
                })
        except Exception as e:
            print(f"yfinance error for Nifty: {e}")
    else:
        # Use mock data
        return generate_mock_nifty_data(days)

    return pd.DataFrame(columns=['date', 'close'])


def calculate_returns(prices_df):
    """Calculate daily returns from price data"""
    returns_list = []

    for symbol in prices_df['symbol'].unique():
        symbol_data = prices_df[prices_df['symbol'] == symbol].sort_values('date')

        # Calculate daily returns
        symbol_data = symbol_data.copy()

        # Fix timezone issue - convert to naive datetime
        # Handle both timezone-aware and timezone-naive datetimes
        symbol_data['date'] = pd.to_datetime(symbol_data['date'])
        if symbol_data['date'].dt.tz is not None:
            # If timezone-aware, convert to naive
            symbol_data['date'] = symbol_data['date'].dt.tz_localize(None)

        symbol_data['return'] = symbol_data['close'].pct_change()
        symbol_data = symbol_data.dropna(subset=['return'])

        returns_list.append(symbol_data[['symbol', 'date', 'return']])

    if returns_list:
        return pd.concat(returns_list, ignore_index=True)

    return pd.DataFrame(columns=['symbol', 'date', 'return'])


def check_symbols_validity(symbols):
    """Check which symbols exist in the database"""
    try:
        results = execute_query(check_symbols_exist_query(), (symbols,))
        valid_symbols = [r['symbol'] for r in results]
        return valid_symbols, list(set(symbols) - set(valid_symbols))
    except Exception as e:
        print(f"Error checking symbols: {e}")
        return [], symbols
