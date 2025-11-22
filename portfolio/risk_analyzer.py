import numpy as np
import pandas as pd
from database.data_loader import get_historical_data, calculate_returns
from portfolio.calculator import calculate_correlation_matrix

def analyze_portfolio_risk(portfolio_data, confidence_level=0.95):
    """
    Comprehensive risk analysis for portfolio
    
    Returns:
    - Correlation matrix
    - Value at Risk (VaR)
    - Conditional VaR (CVaR)
    - Risk contribution by holding
    - Concentration risk metrics
    """
    all_symbols = list(portfolio_data['family_holdings'].keys())
    
    # Get correlation matrix
    corr_matrix = calculate_correlation_matrix(all_symbols)
    
    # Get historical data for VaR calculation
    hist_df = get_historical_data(all_symbols)
    returns_df = calculate_returns(hist_df)
    
    if returns_df.empty:
        return {
            'correlation_matrix': corr_matrix,
            'var': None,
            'cvar': None,
            'risk_contributions': [],
            'concentration_risk': {}
        }
    
    # Calculate portfolio returns
    returns_pivot = returns_df.pivot(index='date', columns='symbol', values='return')
    returns_pivot = returns_pivot.fillna(0)
    
    # Get portfolio weights
    weights = np.array([
        portfolio_data['family_holdings'][s]['weight'] / 100
        for s in all_symbols if s in returns_pivot.columns
    ])
    
    available_symbols = [s for s in all_symbols if s in returns_pivot.columns]
    returns_matrix = returns_pivot[available_symbols]
    
    # Calculate portfolio daily returns
    portfolio_returns = returns_matrix.dot(weights)
    
    # Calculate VaR
    var = calculate_var(portfolio_returns, confidence_level)
    
    # Calculate CVaR (Expected Shortfall)
    cvar = calculate_cvar(portfolio_returns, confidence_level)
    
    # Risk contribution analysis
    risk_contributions = calculate_risk_contribution(
        returns_matrix, weights, available_symbols
    )
    
    # Concentration risk metrics
    concentration = analyze_concentration_risk(portfolio_data)
    
    return {
        'correlation_matrix': corr_matrix,
        'var': var,
        'cvar': cvar,
        'risk_contributions': risk_contributions,
        'concentration_risk': concentration
    }

def calculate_var(returns, confidence_level=0.95):
    """Calculate Value at Risk"""
    if len(returns) == 0:
        return None
    
    var = np.percentile(returns, (1 - confidence_level) * 100)
    
    return {
        'daily_var': var,
        'annual_var': var * np.sqrt(252),
        'confidence_level': confidence_level
    }

def calculate_cvar(returns, confidence_level=0.95):
    """Calculate Conditional VaR (Expected Shortfall)"""
    if len(returns) == 0:
        return None
    
    var_threshold = np.percentile(returns, (1 - confidence_level) * 100)
    cvar = returns[returns <= var_threshold].mean()
    
    return {
        'daily_cvar': cvar,
        'annual_cvar': cvar * np.sqrt(252),
        'confidence_level': confidence_level
    }

def calculate_risk_contribution(returns_matrix, weights, symbols):
    """Calculate risk contribution of each holding"""
    cov_matrix = returns_matrix.cov()
    
    # Portfolio variance
    portfolio_var = np.dot(weights.T, np.dot(cov_matrix, weights))
    portfolio_vol = np.sqrt(portfolio_var)
    
    # Marginal contribution to risk
    marginal_contrib = np.dot(cov_matrix, weights) / portfolio_vol
    
    # Risk contribution
    risk_contrib = weights * marginal_contrib
    
    # Percentage contribution
    risk_contrib_pct = (risk_contrib / portfolio_vol) * 100
    
    contributions = []
    for i, symbol in enumerate(symbols):
        contributions.append({
            'symbol': symbol,
            'weight': weights[i] * 100,
            'risk_contribution': risk_contrib_pct[i],
            'marginal_risk': marginal_contrib[i]
        })
    
    # Sort by risk contribution
    contributions.sort(key=lambda x: abs(x['risk_contribution']), reverse=True)
    
    return contributions

def analyze_concentration_risk(portfolio_data):
    """Analyze concentration risk metrics"""
    holdings = portfolio_data['family_holdings']
    
    # Calculate HHI (Herfindahl-Hirschman Index)
    weights = [h['weight'] / 100 for h in holdings.values()]
    hhi = sum([w**2 for w in weights]) * 10000  # Scaled to 0-10000
    
    # Top holdings concentration
    sorted_holdings = sorted(holdings.items(), key=lambda x: x[1]['weight'], reverse=True)
    
    top_1_concentration = sorted_holdings[0][1]['weight'] if len(sorted_holdings) > 0 else 0
    top_3_concentration = sum([h[1]['weight'] for h in sorted_holdings[:3]]) if len(sorted_holdings) >= 3 else sum([h[1]['weight'] for h in sorted_holdings])
    top_5_concentration = sum([h[1]['weight'] for h in sorted_holdings[:5]]) if len(sorted_holdings) >= 5 else sum([h[1]['weight'] for h in sorted_holdings])
    
    # Determine concentration level
    if top_3_concentration > 75:
        concentration_level = "Very High"
        risk_rating = "High Risk"
    elif top_3_concentration > 50:
        concentration_level = "High"
        risk_rating = "Moderate-High Risk"
    elif top_3_concentration > 30:
        concentration_level = "Moderate"
        risk_rating = "Moderate Risk"
    else:
        concentration_level = "Low"
        risk_rating = "Low Risk"
    
    return {
        'hhi': hhi,
        'top_1_concentration': top_1_concentration,
        'top_3_concentration': top_3_concentration,
        'top_5_concentration': top_5_concentration,
        'concentration_level': concentration_level,
        'risk_rating': risk_rating,
        'effective_holdings': 1 / sum([w**2 for w in weights]) if weights else 0
    }

def simulate_scenarios(portfolio_data, scenarios):
    """
    Simulate portfolio performance under different scenarios
    
    scenarios: list of dicts with {name, stock_changes}
    stock_changes: dict of {symbol: percentage_change}
    """
    results = []
    
    for scenario in scenarios:
        scenario_value = 0
        
        for symbol, data in portfolio_data['family_holdings'].items():
            current_value = data['value']
            change = scenario['stock_changes'].get(symbol, 0)
            new_value = current_value * (1 + change / 100)
            scenario_value += new_value
        
        current_value = portfolio_data['family']['total_value']
        value_change = scenario_value - current_value
        pct_change = (value_change / current_value * 100) if current_value > 0 else 0
        
        results.append({
            'scenario': scenario['name'],
            'current_value': current_value,
            'scenario_value': scenario_value,
            'value_change': value_change,
            'pct_change': pct_change
        })
    
    return results

def get_default_scenarios():
    """Get predefined market scenarios"""
    return [
        {
            'name': 'Market Crash (-20%)',
            'stock_changes': {}  # All stocks -20%
        },
        {
            'name': 'Market Rally (+15%)',
            'stock_changes': {}  # All stocks +15%
        },
        {
            'name': 'Tech Selloff',
            'stock_changes': {
                'TCS': -15,
                'INFY': -15,
                'WIPRO': -15,
                'TECH': -15
            }
        },
        {
            'name': 'Banking Rally',
            'stock_changes': {
                'HDFCBANK': 20,
                'ICICIBANK': 18,
                'AXISBANK': 22,
                'SBIN': 25
            }
        }
    ]

def apply_scenario_to_all(scenario, all_symbols, default_change):
    """Apply a default change to all symbols in a scenario"""
    if not scenario['stock_changes']:
        scenario['stock_changes'] = {symbol: default_change for symbol in all_symbols}
    else:
        # Apply default to symbols not in the scenario
        for symbol in all_symbols:
            if symbol not in scenario['stock_changes']:
                scenario['stock_changes'][symbol] = 0
    
    return scenario
