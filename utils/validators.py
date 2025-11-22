import re
import json

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_portfolio_json(json_input):
    """
    Validate portfolio JSON structure and content
    Returns: (is_valid, error_message)
    """
    # Check if json_input is a dict
    if not isinstance(json_input, dict):
        try:
            json_input = json.loads(json_input)
        except:
            return False, "Invalid JSON format"
    
    # Check required fields
    if 'email' not in json_input:
        return False, "Missing 'email' field"
    
    if 'investor' not in json_input:
        return False, "Missing 'investor' field"
    
    # Validate email
    email = json_input['email']
    if not validate_email(email):
        return False, f"Invalid email format: {email}"
    
    # Validate investors
    investors = json_input['investor']
    if not isinstance(investors, list):
        return False, "'investor' must be a list"
    
    if len(investors) == 0:
        return False, "At least one investor required"
    
    if len(investors) > 20:
        return False, "Maximum 20 family members allowed"
    
    # Track investor IDs for uniqueness
    investor_ids = set()
    
    for idx, investor in enumerate(investors):
        # Check required fields
        if 'id' not in investor:
            return False, f"Investor {idx + 1}: Missing 'id' field"
        
        if 'name' not in investor:
            return False, f"Investor {idx + 1}: Missing 'name' field"
        
        if 'stocks' not in investor:
            return False, f"Investor {idx + 1}: Missing 'stocks' field"
        
        # Validate investor ID
        investor_id = investor['id']
        if not investor_id or not isinstance(investor_id, str):
            return False, f"Investor {idx + 1}: Invalid ID"
        
        if investor_id in investor_ids:
            return False, f"Duplicate investor ID: {investor_id}"
        
        investor_ids.add(investor_id)
        
        # Validate stocks
        stocks = investor['stocks']
        if not isinstance(stocks, list):
            return False, f"Investor {investor_id}: 'stocks' must be a list"
        
        if len(stocks) == 0:
            return False, f"Investor {investor_id}: At least one stock required"
        
        if len(stocks) > 50:
            return False, f"Investor {investor_id}: Maximum 50 stocks allowed"
        
        for stock_idx, stock in enumerate(stocks):
            # Check required fields
            if 'symbol' not in stock:
                return False, f"Investor {investor_id}, Stock {stock_idx + 1}: Missing 'symbol' field"
            
            if 'quantity' not in stock:
                return False, f"Investor {investor_id}, Stock {stock_idx + 1}: Missing 'quantity' field"
            
            # Validate symbol
            symbol = stock['symbol']
            if not symbol or not isinstance(symbol, str):
                return False, f"Investor {investor_id}: Invalid symbol format"
            
            # Validate quantity
            try:
                quantity = float(stock['quantity'])
                if quantity <= 0:
                    return False, f"Investor {investor_id}, Symbol {symbol}: Quantity must be positive"
            except (ValueError, TypeError):
                return False, f"Investor {investor_id}, Symbol {symbol}: Invalid quantity"
            
            # Validate cost_basis if present
            if 'cost_basis' in stock:
                try:
                    cost_basis = float(stock['cost_basis'])
                    if cost_basis < 0:
                        return False, f"Investor {investor_id}, Symbol {symbol}: Cost basis cannot be negative"
                except (ValueError, TypeError):
                    return False, f"Investor {investor_id}, Symbol {symbol}: Invalid cost_basis"
    
    return True, "Valid"

def sanitize_json_input(json_input):
    """Sanitize and normalize JSON input"""
    if isinstance(json_input, str):
        json_input = json.loads(json_input)
    
    # Ensure all numeric fields are proper numbers
    for investor in json_input.get('investor', []):
        for stock in investor.get('stocks', []):
            stock['quantity'] = float(stock['quantity'])
            if 'cost_basis' in stock:
                stock['cost_basis'] = float(stock['cost_basis'])
            else:
                stock['cost_basis'] = 0
    
    return json_input
