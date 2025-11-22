import json
import sys
from utils.validators import validate_portfolio_json, sanitize_json_input
from portfolio.aggregator import process_portfolio_data

def test_phase1():
    """Test Phase 1: Core data pipeline"""
    
    print("=" * 60)
    print("PHASE 1 TEST: Core Data Pipeline")
    print("=" * 60)
    
    # Test 1: Load and validate JSON
    print("\n1. Testing JSON validation...")
    try:
        with open('sample_simple.json', 'r') as f:
            json_data = json.load(f)
        
        is_valid, message = validate_portfolio_json(json_data)
        if is_valid:
            print("✓ JSON validation passed")
        else:
            print(f"✗ JSON validation failed: {message}")
            return
    except Exception as e:
        print(f"✗ Error loading JSON: {e}")
        return
    
    # Test 2: Sanitize input
    print("\n2. Sanitizing input...")
    try:
        sanitized_data = sanitize_json_input(json_data)
        print("✓ Input sanitized")
    except Exception as e:
        print(f"✗ Error sanitizing input: {e}")
        return
    
    # Test 3: Process portfolio
    print("\n3. Processing portfolio...")
    try:
        result = process_portfolio_data(sanitized_data)
        print("✓ Portfolio processed successfully")
        
        # Print summary
        print("\n" + "=" * 60)
        print("PORTFOLIO SUMMARY")
        print("=" * 60)
        
        family = result['family']
        print(f"\nFamily Email: {family['email']}")
        print(f"Total Value: ₹{family['total_value']:,.2f}")
        print(f"Total Gain: ₹{family['total_gain']:,.2f} ({family['total_gain_pct']:.2f}%)")
        print(f"Members: {family['member_count']}")
        print(f"Unique Stocks: {family['unique_stocks']}")
        print(f"Risk Score: {family['risk_score']}/10")
        
        print(f"\nFamily Metrics:")
        print(f"  Volatility: {family['metrics']['volatility']:.4f}")
        print(f"  Expected Return: {family['metrics']['expected_return']:.4f}")
        print(f"  Sharpe Ratio: {family['metrics']['sharpe_ratio']:.4f}")
        print(f"  Beta: {family['metrics']['beta']:.4f}")
        print(f"  Diversification Score: {family['metrics']['diversification_score']:.2f}/10")
        
        print(f"\n{'-' * 60}")
        print("MEMBER DETAILS")
        print("-" * 60)
        
        for member in result['members']:
            print(f"\n{member['name']} ({member['id']})")
            print(f"  Portfolio Value: ₹{member['value']:,.2f}")
            print(f"  Gain: ₹{member['gain']:,.2f} ({member['gain_pct']:.2f}%)")
            print(f"  Holdings: {member['holdings_count']} stocks")
            print(f"  Sharpe Ratio: {member['metrics']['sharpe_ratio']:.4f}")
            
            print(f"\n  Holdings:")
            for holding in member['holdings']:
                print(f"    {holding['symbol']}: {holding['quantity']} shares @ ₹{holding['current_price']:.2f} = ₹{holding['value']:,.2f} ({holding['weight']:.1f}%)")
        
        if result['overlaps']:
            print(f"\n{'-' * 60}")
            print("OVERLAPPING HOLDINGS (Risk Alert!)")
            print("-" * 60)
            for symbol, owners in result['overlaps'].items():
                print(f"  {symbol}: Owned by {', '.join(owners)}")
        
        print("\n" + "=" * 60)
        print("✓ PHASE 1 COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"✗ Error processing portfolio: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    test_phase1()
