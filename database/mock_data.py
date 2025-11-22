"""
Mock data provider for testing without yfinance/database access
This will be replaced by actual data sources in production
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Mock current prices (₹)
MOCK_PRICES = {
    'RELIANCE': 2850.50,
    'TCS': 3750.25,
    'INFY': 1680.75,
    'HDFCBANK': 1720.00,
    'ICICIBANK': 1050.50,
    'WIPRO': 465.30,
    'BHARTIARTL': 890.75,
    'ITC': 475.60,
    'HINDUNILVR': 2420.30,
    'SBIN': 625.80,
    'AXISBANK': 1145.25,
    'LT': 3520.00,
    'MARUTI': 12350.00,
    'SUNPHARMA': 1680.50,
    'TATAMOTORS': 965.40
}

def generate_mock_historical_data(symbol, days=252):
    """Generate realistic mock historical data"""
    base_price = MOCK_PRICES.get(symbol, 1000)
    
    # Generate dates
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=days, freq='D')
    
    # Generate price series with realistic volatility
    returns = np.random.normal(0.0005, 0.02, days)  # Daily returns
    prices = [base_price * 0.85]  # Start 15% lower
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Smooth the trend to end at current price
    adjustment_factor = base_price / prices[-1]
    prices = [p * adjustment_factor for p in prices]
    
    df = pd.DataFrame({
        'symbol': symbol,
        'date': dates,
        'close': prices
    })
    
    return df

def generate_mock_nifty_data(days=252):
    """Generate mock Nifty 50 index data"""
    base_price = 22000
    
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=days, freq='D')
    
    returns = np.random.normal(0.0003, 0.015, days)
    prices = [base_price * 0.90]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    adjustment_factor = base_price / prices[-1]
    prices = [p * adjustment_factor for p in prices]
    
    df = pd.DataFrame({
        'date': dates,
        'close': prices
    })
    
    return df

# Flag to track if we're using mock data
USING_MOCK_DATA = True
