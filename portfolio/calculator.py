import numpy as np
import pandas as pd
from database.data_loader import get_historical_data, get_nifty50_data, calculate_returns

RISK_FREE_RATE = 0.065  # 6.5% for India
TRADING_DAYS = 252


def normalize_datetime_index(series_or_df):
    """
    Normalize datetime index to be timezone-naive
    Works with both Series and DataFrame
    """
    if isinstance(series_or_df.index, pd.DatetimeIndex):
        if series_or_df.index.tz is not None:
            # Remove timezone information
            new_obj = series_or_df.copy()
            new_obj.index = new_obj.index.tz_localize(None)
            return new_obj
    return series_or_df


def calculate_expected_return(returns):
    """Calculate annualized expected return"""
    return np.mean(returns) * TRADING_DAYS


def calculate_volatility(returns):
    """Calculate annualized volatility"""
    return np.std(returns) * np.sqrt(TRADING_DAYS)


def calculate_sharpe_ratio(returns, risk_free_rate=RISK_FREE_RATE):
    """Calculate Sharpe ratio"""
    expected_return = calculate_expected_return(returns)
    volatility = calculate_volatility(returns)

    if volatility == 0:
        return 0

    excess_return = expected_return - risk_free_rate
    return excess_return / volatility


def calculate_beta(stock_returns, market_returns):
    """Calculate beta against market (Nifty 50)"""
    if len(stock_returns) == 0 or len(market_returns) == 0:
        return 1.0

    # Normalize both series to timezone-naive
    stock_returns = normalize_datetime_index(stock_returns)
    market_returns = normalize_datetime_index(market_returns)

    # Align returns by date
    stock_df = pd.DataFrame({'return': stock_returns.values}, index=stock_returns.index)
    market_df = pd.DataFrame({'return': market_returns.values}, index=market_returns.index)

    # Join the dataframes
    combined = stock_df.join(market_df, how='inner', lsuffix='_stock', rsuffix='_market')

    if len(combined) < 2:
        return 1.0

    covariance = np.cov(combined['return_stock'], combined['return_market'])[0][1]
    market_variance = np.var(combined['return_market'])

    if market_variance == 0:
        return 1.0

    return covariance / market_variance


def calculate_stock_metrics(symbol, lookback_days=252):
    """
    Calculate all metrics for a single stock
    Returns: dict with volatility, expected_return, sharpe_ratio, beta
    """
    # Get historical data
    hist_df = get_historical_data([symbol], days=lookback_days)

    if hist_df.empty:
        return {
            'volatility': 0,
            'expected_return': 0,
            'sharpe_ratio': 0,
            'beta': 1.0
        }

    # Calculate returns
    returns_df = calculate_returns(hist_df)
    stock_returns = returns_df['return']

    if len(stock_returns) == 0:
        return {
            'volatility': 0,
            'expected_return': 0,
            'sharpe_ratio': 0,
            'beta': 1.0
        }

    # Get Nifty 50 data for beta
    nifty_df = get_nifty50_data(days=lookback_days)
    market_returns = pd.Series(dtype=float)

    if not nifty_df.empty:
        nifty_df['return'] = nifty_df['close'].pct_change()
        nifty_df = nifty_df.dropna(subset=['return'])
        nifty_df.set_index('date', inplace=True)
        market_returns = nifty_df['return']

        # Normalize market returns timezone
        market_returns = normalize_datetime_index(market_returns)

    # Calculate metrics
    volatility = calculate_volatility(stock_returns)
    expected_return = calculate_expected_return(stock_returns)
    sharpe_ratio = calculate_sharpe_ratio(stock_returns)

    # Set returns index to date for beta calculation
    returns_df_indexed = returns_df.set_index('date')
    stock_returns_indexed = returns_df_indexed['return']

    # Normalize stock returns timezone
    stock_returns_indexed = normalize_datetime_index(stock_returns_indexed)

    beta = calculate_beta(stock_returns_indexed, market_returns) if not market_returns.empty else 1.0

    return {
        'volatility': round(volatility, 4),
        'expected_return': round(expected_return, 4),
        'sharpe_ratio': round(sharpe_ratio, 4),
        'beta': round(beta, 4)
    }


def calculate_portfolio_metrics(holdings_data, returns_df):
    """
    Calculate portfolio-level metrics
    holdings_data: list of dicts with {symbol, weight, value}
    returns_df: DataFrame with returns for all symbols
    """
    if not holdings_data or returns_df.empty:
        return {
            'volatility': 0,
            'expected_return': 0,
            'sharpe_ratio': 0,
            'beta': 1.0
        }

    # Create returns matrix
    returns_pivot = returns_df.pivot(index='date', columns='symbol', values='return')
    returns_pivot = returns_pivot.fillna(0)

    # Get weights
    symbols = [h['symbol'] for h in holdings_data]
    weights = np.array([h['weight'] for h in holdings_data])

    # Filter returns to only include our symbols
    available_symbols = [s for s in symbols if s in returns_pivot.columns]
    if not available_symbols:
        return {
            'volatility': 0,
            'expected_return': 0,
            'sharpe_ratio': 0,
            'beta': 1.0
        }

    returns_matrix = returns_pivot[available_symbols]

    # Adjust weights if some symbols are missing
    if len(available_symbols) < len(symbols):
        weight_map = {h['symbol']: h['weight'] for h in holdings_data}
        weights = np.array([weight_map.get(s, 0) for s in available_symbols])
        weights = weights / weights.sum()  # Renormalize

    # Calculate portfolio returns
    portfolio_returns = returns_matrix.dot(weights)

    # Normalize portfolio returns timezone
    portfolio_returns = normalize_datetime_index(portfolio_returns)

    # Calculate metrics
    volatility = calculate_volatility(portfolio_returns)
    expected_return = calculate_expected_return(portfolio_returns)
    sharpe_ratio = calculate_sharpe_ratio(portfolio_returns)

    # Calculate portfolio beta
    nifty_df = get_nifty50_data()
    market_returns = pd.Series(dtype=float)

    if not nifty_df.empty:
        nifty_df['return'] = nifty_df['close'].pct_change()
        nifty_df = nifty_df.dropna(subset=['return'])
        nifty_df.set_index('date', inplace=True)
        market_returns = nifty_df['return']

        # Normalize market returns timezone
        market_returns = normalize_datetime_index(market_returns)

    beta = calculate_beta(portfolio_returns, market_returns) if not market_returns.empty else 1.0

    return {
        'volatility': round(volatility, 4),
        'expected_return': round(expected_return, 4),
        'sharpe_ratio': round(sharpe_ratio, 4),
        'beta': round(beta, 4)
    }


def calculate_correlation_matrix(symbols, lookback_days=252):
    """Calculate correlation matrix for given symbols"""
    hist_df = get_historical_data(symbols, days=lookback_days)

    if hist_df.empty:
        return pd.DataFrame()

    returns_df = calculate_returns(hist_df)
    returns_pivot = returns_df.pivot(index='date', columns='symbol', values='return')

    return returns_pivot.corr()


def calculate_diversification_score(holdings_count, correlation_matrix):
    """
    Calculate diversification score (0-10)
    Higher is better (more diversified)
    """
    if holdings_count <= 1:
        return 0

    if correlation_matrix.empty or len(correlation_matrix) < 2:
        return 5  # Default mid-score for small portfolios

    # Average correlation (excluding diagonal)
    upper_triangle = np.triu_indices_from(correlation_matrix.values, k=1)
    if len(upper_triangle[0]) == 0:
        return 5

    avg_correlation = correlation_matrix.values[upper_triangle].mean()

    # Handle NaN
    if np.isnan(avg_correlation):
        return 5

    # Score based on number of holdings and correlation
    holdings_score = min(holdings_count / 20, 1) * 5  # Max 5 points for holdings
    correlation_score = (1 - avg_correlation) * 5  # Max 5 points for low correlation

    return round(holdings_score + correlation_score, 2)
