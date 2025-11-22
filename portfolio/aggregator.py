import pandas as pd
import numpy as np
from database.data_loader import get_current_price, get_historical_data, calculate_returns
from portfolio.calculator import (
    calculate_stock_metrics,
    calculate_portfolio_metrics,
    calculate_correlation_matrix,
    calculate_diversification_score
)

def process_portfolio_data(json_input):
    """
    Process portfolio JSON and return comprehensive analysis
    
    Input JSON structure:
    {
        "email": "family@example.com",
        "investor": [
            {
                "id": "INV001",
                "name": "Member Name",
                "stocks": [
                    {
                        "symbol": "RELIANCE",
                        "quantity": "100",
                        "cost_basis": "2450.50"
                    }
                ]
            }
        ]
    }
    
    Output: Comprehensive portfolio analysis dict
    """
    email = json_input.get('email', '')
    investors = json_input.get('investor', [])
    
    # Collect all unique symbols
    all_symbols = set()
    for investor in investors:
        for stock in investor.get('stocks', []):
            all_symbols.add(stock['symbol'])
    
    all_symbols = list(all_symbols)
    
    # Get current prices for all symbols
    current_prices = {}
    for symbol in all_symbols:
        price = get_current_price(symbol)
        if price:
            current_prices[symbol] = price
    
    # Get historical data for all symbols
    hist_df = get_historical_data(all_symbols)
    returns_df = calculate_returns(hist_df)
    
    # Calculate stock metrics
    stock_metrics = {}
    for symbol in all_symbols:
        stock_metrics[symbol] = calculate_stock_metrics(symbol)
    
    # Process each member
    members_data = []
    family_total_value = 0
    family_total_cost = 0
    family_holdings = {}  # Track family-wide holdings
    
    for investor in investors:
        member_id = investor.get('id', '')
        member_name = investor.get('name', '')
        stocks = investor.get('stocks', [])
        
        member_holdings = []
        member_total_value = 0
        member_total_cost = 0
        
        for stock in stocks:
            symbol = stock['symbol']
            quantity = float(stock['quantity'])
            cost_basis = float(stock.get('cost_basis', 0))
            
            current_price = current_prices.get(symbol, 0)
            value = quantity * current_price
            total_cost = quantity * cost_basis if cost_basis > 0 else 0
            gain = value - total_cost if total_cost > 0 else 0
            
            member_total_value += value
            member_total_cost += total_cost
            
            # Track family-wide holdings
            if symbol not in family_holdings:
                family_holdings[symbol] = {
                    'quantity': 0,
                    'value': 0,
                    'cost': 0,
                    'owners': []
                }
            family_holdings[symbol]['quantity'] += quantity
            family_holdings[symbol]['value'] += value
            family_holdings[symbol]['cost'] += total_cost
            family_holdings[symbol]['owners'].append(member_name)
            
            holding = {
                'symbol': symbol,
                'quantity': quantity,
                'current_price': round(current_price, 2),
                'value': round(value, 2),
                'cost_basis': cost_basis,
                'total_cost': round(total_cost, 2),
                'gain': round(gain, 2),
                'gain_pct': round((gain / total_cost * 100) if total_cost > 0 else 0, 2),
                'weight': 0,  # Will calculate after we have member total
                'volatility': stock_metrics.get(symbol, {}).get('volatility', 0),
                'expected_return': stock_metrics.get(symbol, {}).get('expected_return', 0),
                'sharpe_ratio': stock_metrics.get(symbol, {}).get('sharpe_ratio', 0),
                'beta': stock_metrics.get(symbol, {}).get('beta', 1.0)
            }
            member_holdings.append(holding)
        
        # Calculate weights
        for holding in member_holdings:
            holding['weight'] = round((holding['value'] / member_total_value * 100) if member_total_value > 0 else 0, 2)
        
        # Calculate member portfolio metrics
        holdings_for_metrics = [
            {'symbol': h['symbol'], 'weight': h['weight'] / 100, 'value': h['value']}
            for h in member_holdings
        ]
        member_metrics = calculate_portfolio_metrics(holdings_for_metrics, returns_df)
        
        # Calculate diversification score
        member_symbols = [h['symbol'] for h in member_holdings]
        corr_matrix = calculate_correlation_matrix(member_symbols)
        diversification_score = calculate_diversification_score(len(member_holdings), corr_matrix)
        
        member_gain_pct = round((member_total_value - member_total_cost) / member_total_cost * 100 if member_total_cost > 0 else 0, 2)
        
        member_data = {
            'id': member_id,
            'name': member_name,
            'value': round(member_total_value, 2),
            'cost': round(member_total_cost, 2),
            'gain': round(member_total_value - member_total_cost, 2),
            'gain_pct': member_gain_pct,
            'holdings_count': len(member_holdings),
            'holdings': member_holdings,
            'metrics': {
                'volatility': member_metrics['volatility'],
                'expected_return': member_metrics['expected_return'],
                'sharpe_ratio': member_metrics['sharpe_ratio'],
                'beta': member_metrics['beta'],
                'diversification_score': diversification_score
            }
        }
        
        members_data.append(member_data)
        family_total_value += member_total_value
        family_total_cost += member_total_cost
    
    # Detect overlapping holdings
    overlapping_stocks = {
        symbol: data['owners']
        for symbol, data in family_holdings.items()
        if len(data['owners']) > 1
    }
    
    # Calculate family-level metrics
    all_family_holdings = []
    for symbol, data in family_holdings.items():
        all_family_holdings.append({
            'symbol': symbol,
            'weight': data['value'] / family_total_value if family_total_value > 0 else 0,
            'value': data['value']
        })
    
    family_metrics = calculate_portfolio_metrics(all_family_holdings, returns_df)
    
    # Calculate family diversification
    family_symbols = list(family_holdings.keys())
    family_corr_matrix = calculate_correlation_matrix(family_symbols)
    family_diversification = calculate_diversification_score(len(family_symbols), family_corr_matrix)
    
    # Calculate risk score (0-10, lower is better)
    risk_score = calculate_risk_score(
        family_metrics['volatility'],
        family_metrics['beta'],
        family_diversification,
        len(overlapping_stocks),
        len(family_symbols)
    )
    
    # Build output
    output = {
        'family': {
            'email': email,
            'total_value': round(family_total_value, 2),
            'total_cost': round(family_total_cost, 2),
            'total_gain': round(family_total_value - family_total_cost, 2),
            'total_gain_pct': round((family_total_value - family_total_cost) / family_total_cost * 100 if family_total_cost > 0 else 0, 2),
            'member_count': len(members_data),
            'total_stocks': len(family_symbols),
            'unique_stocks': len(family_symbols),
            'overlapping_stocks': len(overlapping_stocks),
            'risk_score': risk_score,
            'metrics': {
                'volatility': family_metrics['volatility'],
                'expected_return': family_metrics['expected_return'],
                'sharpe_ratio': family_metrics['sharpe_ratio'],
                'beta': family_metrics['beta'],
                'diversification_score': family_diversification
            }
        },
        'members': members_data,
        'overlaps': overlapping_stocks,
        'family_holdings': {
            symbol: {
                'quantity': data['quantity'],
                'value': round(data['value'], 2),
                'weight': round(data['value'] / family_total_value * 100 if family_total_value > 0 else 0, 2),
                'owners': data['owners']
            }
            for symbol, data in family_holdings.items()
        }
    }
    
    return output

def calculate_risk_score(volatility, beta, diversification, overlap_count, total_stocks):
    """
    Calculate overall risk score (0-10, where 10 is highest risk)
    """
    # Volatility component (0-3 points)
    vol_score = min(volatility * 10, 3)
    
    # Beta component (0-2 points)
    beta_score = min(abs(beta - 1) * 2, 2)
    
    # Diversification component (0-3 points, inverted)
    div_score = max(0, 3 - (diversification / 10 * 3))
    
    # Overlap penalty (0-2 points)
    overlap_score = min(overlap_count / total_stocks * 2 if total_stocks > 0 else 0, 2)
    
    total_score = vol_score + beta_score + div_score + overlap_score
    
    return round(min(total_score, 10), 2)
