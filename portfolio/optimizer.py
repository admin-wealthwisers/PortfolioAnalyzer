import numpy as np
import pandas as pd
from scipy.optimize import minimize
from database.data_loader import get_historical_data, calculate_returns

RISK_FREE_RATE = 0.065
TRADING_DAYS = 252

def get_returns_and_cov(symbols, lookback_days=252):
    """
    Get historical returns and covariance matrix for symbols
    Returns: (expected_returns, cov_matrix)
    """
    # Get historical data
    hist_df = get_historical_data(symbols, days=lookback_days)
    
    if hist_df.empty:
        return None, None
    
    # Calculate returns
    returns_df = calculate_returns(hist_df)
    
    # Pivot to get returns matrix
    returns_pivot = returns_df.pivot(index='date', columns='symbol', values='return')
    returns_pivot = returns_pivot.fillna(0)
    
    # Calculate expected returns (annualized)
    expected_returns = returns_pivot.mean() * TRADING_DAYS
    
    # Calculate covariance matrix (annualized)
    cov_matrix = returns_pivot.cov() * TRADING_DAYS
    
    return expected_returns, cov_matrix

def optimize_portfolio(symbols, current_weights=None, target_return=None, method='max_sharpe'):
    """
    Optimize portfolio allocation
    
    Methods:
    - 'max_sharpe': Maximize Sharpe ratio
    - 'min_volatility': Minimize portfolio volatility
    - 'target_return': Maximize Sharpe with target return constraint
    - 'equal_weight': Equal allocation
    """
    expected_returns, cov_matrix = get_returns_and_cov(symbols)
    
    if expected_returns is None:
        return None
    
    n_assets = len(symbols)
    
    # Equal weight baseline
    if method == 'equal_weight':
        weights = np.array([1/n_assets] * n_assets)
        portfolio_return = np.dot(weights, expected_returns)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe = (portfolio_return - RISK_FREE_RATE) / portfolio_vol
        
        return {
            'weights': dict(zip(symbols, weights)),
            'expected_return': portfolio_return,
            'volatility': portfolio_vol,
            'sharpe_ratio': sharpe
        }
    
    # Optimization objective functions
    def portfolio_volatility(weights):
        return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    
    def portfolio_return(weights):
        return np.dot(weights, expected_returns)
    
    def negative_sharpe(weights):
        ret = portfolio_return(weights)
        vol = portfolio_volatility(weights)
        return -(ret - RISK_FREE_RATE) / vol
    
    # Constraints and bounds
    constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]  # Sum to 1
    
    if target_return is not None:
        constraints.append({
            'type': 'eq',
            'fun': lambda x: portfolio_return(x) - target_return
        })
    
    bounds = tuple((0, 1) for _ in range(n_assets))  # No short selling
    
    # Initial guess
    if current_weights is not None:
        initial_weights = np.array([current_weights.get(s, 1/n_assets) for s in symbols])
        initial_weights = initial_weights / initial_weights.sum()
    else:
        initial_weights = np.array([1/n_assets] * n_assets)
    
    # Optimize
    if method == 'max_sharpe' or method == 'target_return':
        result = minimize(negative_sharpe, initial_weights, method='SLSQP',
                         bounds=bounds, constraints=constraints)
    elif method == 'min_volatility':
        result = minimize(portfolio_volatility, initial_weights, method='SLSQP',
                         bounds=bounds, constraints=constraints)
    else:
        return None
    
    if not result.success:
        return None
    
    optimal_weights = result.x
    
    return {
        'weights': dict(zip(symbols, optimal_weights)),
        'expected_return': portfolio_return(optimal_weights),
        'volatility': portfolio_volatility(optimal_weights),
        'sharpe_ratio': -result.fun if method in ['max_sharpe', 'target_return'] else 
                       (portfolio_return(optimal_weights) - RISK_FREE_RATE) / portfolio_volatility(optimal_weights)
    }

def generate_efficient_frontier(symbols, n_points=50):
    """Generate efficient frontier curve"""
    expected_returns, cov_matrix = get_returns_and_cov(symbols)
    
    if expected_returns is None:
        return None
    
    # Get min and max possible returns
    min_ret = expected_returns.min()
    max_ret = expected_returns.max()
    
    target_returns = np.linspace(min_ret, max_ret, n_points)
    
    frontier_volatility = []
    frontier_returns = []
    frontier_sharpe = []
    
    for target_ret in target_returns:
        result = optimize_portfolio(symbols, target_return=target_ret)
        
        if result is not None:
            frontier_returns.append(result['expected_return'])
            frontier_volatility.append(result['volatility'])
            frontier_sharpe.append(result['sharpe_ratio'])
        else:
            frontier_returns.append(target_ret)
            frontier_volatility.append(np.nan)
            frontier_sharpe.append(np.nan)
    
    return {
        'returns': frontier_returns,
        'volatility': frontier_volatility,
        'sharpe': frontier_sharpe
    }

def calculate_rebalancing_trades(current_holdings, target_weights, total_value):
    """
    Calculate trades needed to rebalance portfolio
    
    current_holdings: list of {symbol, quantity, current_price, value}
    target_weights: dict of {symbol: weight}
    total_value: total portfolio value
    
    Returns: list of trades with buy/sell recommendations
    """
    trades = []
    
    for symbol, target_weight in target_weights.items():
        target_value = total_value * target_weight
        
        # Find current holding
        current_holding = next((h for h in current_holdings if h['symbol'] == symbol), None)
        
        if current_holding:
            current_value = current_holding['value']
            current_price = current_holding['current_price']
            current_quantity = current_holding['quantity']
        else:
            current_value = 0
            current_price = 0  # Will need to fetch
            current_quantity = 0
        
        value_diff = target_value - current_value
        
        if abs(value_diff) > total_value * 0.01:  # 1% threshold
            if current_price > 0:
                quantity_diff = value_diff / current_price
            else:
                quantity_diff = 0
            
            action = 'BUY' if value_diff > 0 else 'SELL'
            
            trades.append({
                'symbol': symbol,
                'action': action,
                'quantity': abs(quantity_diff),
                'value': abs(value_diff),
                'current_weight': (current_value / total_value * 100) if total_value > 0 else 0,
                'target_weight': target_weight * 100,
                'weight_change': (target_weight * 100) - ((current_value / total_value * 100) if total_value > 0 else 0)
            })
    
    # Sort by absolute value change
    trades.sort(key=lambda x: abs(x['value']), reverse=True)
    
    return trades

def optimize_family_portfolio(portfolio_data, method='max_sharpe', target_return=None):
    """
    Optimize family portfolio and provide rebalancing recommendations
    """
    # Get all unique symbols
    all_symbols = list(portfolio_data['family_holdings'].keys())
    
    # Get current weights
    current_weights = {
        symbol: data['weight'] / 100
        for symbol, data in portfolio_data['family_holdings'].items()
    }
    
    # Optimize
    optimized = optimize_portfolio(all_symbols, current_weights, target_return, method)
    
    if optimized is None:
        return None
    
    # Calculate current portfolio metrics
    expected_returns, cov_matrix = get_returns_and_cov(all_symbols)
    current_weights_array = np.array([current_weights[s] for s in all_symbols])
    
    current_return = np.dot(current_weights_array, expected_returns)
    current_vol = np.sqrt(np.dot(current_weights_array.T, np.dot(cov_matrix, current_weights_array)))
    current_sharpe = (current_return - RISK_FREE_RATE) / current_vol
    
    # Aggregate current holdings
    all_holdings = []
    for member in portfolio_data['members']:
        all_holdings.extend(member['holdings'])
    
    # Merge holdings by symbol
    holdings_by_symbol = {}
    for h in all_holdings:
        symbol = h['symbol']
        if symbol not in holdings_by_symbol:
            holdings_by_symbol[symbol] = {
                'symbol': symbol,
                'quantity': 0,
                'current_price': h['current_price'],
                'value': 0
            }
        holdings_by_symbol[symbol]['quantity'] += h['quantity']
        holdings_by_symbol[symbol]['value'] += h['value']
    
    merged_holdings = list(holdings_by_symbol.values())
    
    # Calculate rebalancing trades
    trades = calculate_rebalancing_trades(
        merged_holdings,
        optimized['weights'],
        portfolio_data['family']['total_value']
    )
    
    return {
        'current': {
            'expected_return': current_return,
            'volatility': current_vol,
            'sharpe_ratio': current_sharpe,
            'weights': current_weights
        },
        'optimized': optimized,
        'trades': trades,
        'improvement': {
            'return_change': optimized['expected_return'] - current_return,
            'volatility_change': optimized['volatility'] - current_vol,
            'sharpe_change': optimized['sharpe_ratio'] - current_sharpe
        }
    }
