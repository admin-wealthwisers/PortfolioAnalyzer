"""
Context builder for LLM chat
Formats portfolio data into context for Claude API
"""

def build_portfolio_context(portfolio_data):
    """Build comprehensive context string for LLM from portfolio data"""
    
    if not portfolio_data:
        return "No portfolio data available."
    
    family = portfolio_data['family']
    members = portfolio_data['members']
    overlaps = portfolio_data['overlaps']
    family_holdings = portfolio_data['family_holdings']
    
    # Build context sections
    context_parts = []
    
    # Family overview
    context_parts.append("# FAMILY PORTFOLIO OVERVIEW")
    context_parts.append(f"Email: {family['email']}")
    context_parts.append(f"Total Value: ₹{family['total_value']:,.2f}")
    context_parts.append(f"Total Gain: ₹{family['total_gain']:,.2f} ({family['total_gain_pct']:.2f}%)")
    context_parts.append(f"Members: {family['member_count']}")
    context_parts.append(f"Unique Stocks: {family['unique_stocks']}")
    context_parts.append(f"Overlapping Stocks: {family['overlapping_stocks']}")
    context_parts.append(f"Risk Score: {family['risk_score']}/10")
    context_parts.append("")
    
    # Family metrics
    context_parts.append("## Family Portfolio Metrics")
    context_parts.append(f"- Volatility: {family['metrics']['volatility']:.4f}")
    context_parts.append(f"- Expected Return: {family['metrics']['expected_return']:.4f}")
    context_parts.append(f"- Sharpe Ratio: {family['metrics']['sharpe_ratio']:.4f}")
    context_parts.append(f"- Beta: {family['metrics']['beta']:.4f}")
    context_parts.append(f"- Diversification Score: {family['metrics']['diversification_score']:.2f}/10")
    context_parts.append("")
    
    # Family holdings
    context_parts.append("## Family Holdings (Aggregated)")
    sorted_holdings = sorted(family_holdings.items(), key=lambda x: x[1]['value'], reverse=True)
    for symbol, data in sorted_holdings:
        context_parts.append(f"- {symbol}: ₹{data['value']:,.2f} ({data['weight']:.1f}%), owned by: {', '.join(data['owners'])}")
    context_parts.append("")
    
    # Overlapping holdings
    if overlaps:
        context_parts.append("## Overlapping Holdings (RISK ALERT)")
        for symbol, owners in overlaps.items():
            context_parts.append(f"- {symbol}: Owned by {len(owners)} members ({', '.join(owners)})")
        context_parts.append("")
    
    # Member details
    context_parts.append("## Individual Member Portfolios")
    for member in members:
        context_parts.append(f"\n### {member['name']} ({member['id']})")
        context_parts.append(f"Portfolio Value: ₹{member['value']:,.2f}")
        context_parts.append(f"Gain: ₹{member['gain']:,.2f} ({member['gain_pct']:.2f}%)")
        context_parts.append(f"Number of Holdings: {member['holdings_count']}")
        context_parts.append(f"Sharpe Ratio: {member['metrics']['sharpe_ratio']:.4f}")
        context_parts.append(f"Diversification Score: {member['metrics']['diversification_score']:.2f}/10")
        
        context_parts.append("\nHoldings:")
        for holding in sorted(member['holdings'], key=lambda x: x['value'], reverse=True):
            context_parts.append(
                f"  - {holding['symbol']}: {holding['quantity']} shares @ ₹{holding['current_price']:.2f} "
                f"= ₹{holding['value']:,.2f} ({holding['weight']:.1f}%), "
                f"Gain: {holding['gain_pct']:.1f}%"
            )
    
    return "\n".join(context_parts)

def build_optimization_context(optimization_result):
    """Build context from optimization results"""
    
    if not optimization_result:
        return "No optimization data available."
    
    context_parts = []
    
    context_parts.append("# PORTFOLIO OPTIMIZATION RESULTS")
    context_parts.append("")
    
    # Current portfolio
    current = optimization_result['current']
    context_parts.append("## Current Portfolio")
    context_parts.append(f"- Expected Return: {current['expected_return']*100:.2f}%")
    context_parts.append(f"- Volatility: {current['volatility']*100:.2f}%")
    context_parts.append(f"- Sharpe Ratio: {current['sharpe_ratio']:.4f}")
    context_parts.append("")
    
    # Optimized portfolio
    optimized = optimization_result['optimized']
    context_parts.append("## Optimized Portfolio")
    context_parts.append(f"- Expected Return: {optimized['expected_return']*100:.2f}%")
    context_parts.append(f"- Volatility: {optimized['volatility']*100:.2f}%")
    context_parts.append(f"- Sharpe Ratio: {optimized['sharpe_ratio']:.4f}")
    context_parts.append("")
    
    # Improvements
    improvement = optimization_result['improvement']
    context_parts.append("## Improvements")
    context_parts.append(f"- Return Change: {improvement['return_change']*100:+.2f}%")
    context_parts.append(f"- Volatility Change: {improvement['volatility_change']*100:+.2f}%")
    context_parts.append(f"- Sharpe Change: {improvement['sharpe_change']:+.4f}")
    context_parts.append("")
    
    # Top rebalancing trades
    context_parts.append("## Key Rebalancing Actions")
    for i, trade in enumerate(optimization_result['trades'][:5], 1):
        context_parts.append(
            f"{i}. {trade['action']} {trade['quantity']:.0f} shares of {trade['symbol']} "
            f"(₹{trade['value']:,.0f}), weight change: {trade['weight_change']:+.1f}%"
        )
    
    return "\n".join(context_parts)

def build_risk_context(risk_data):
    """Build context from risk analysis"""
    
    if not risk_data:
        return "No risk data available."
    
    context_parts = []
    
    context_parts.append("# RISK ANALYSIS RESULTS")
    context_parts.append("")
    
    # Concentration risk
    conc = risk_data['concentration_risk']
    context_parts.append("## Concentration Risk")
    context_parts.append(f"- HHI Index: {conc['hhi']:.2f}")
    context_parts.append(f"- Top 1 Stock: {conc['top_1_concentration']:.1f}%")
    context_parts.append(f"- Top 3 Stocks: {conc['top_3_concentration']:.1f}%")
    context_parts.append(f"- Top 5 Stocks: {conc['top_5_concentration']:.1f}%")
    context_parts.append(f"- Concentration Level: {conc['concentration_level']}")
    context_parts.append(f"- Risk Rating: {conc['risk_rating']}")
    context_parts.append(f"- Effective Holdings: {conc['effective_holdings']:.2f}")
    context_parts.append("")
    
    # VaR
    if risk_data['var']:
        var = risk_data['var']
        cvar = risk_data['cvar']
        context_parts.append("## Value at Risk (VaR)")
        context_parts.append(f"- Confidence Level: {var['confidence_level']*100:.0f}%")
        context_parts.append(f"- Daily VaR: {var['daily_var']*100:.2f}%")
        context_parts.append(f"- Annual VaR: {var['annual_var']*100:.2f}%")
        context_parts.append(f"- Daily CVaR: {cvar['daily_cvar']*100:.2f}%")
        context_parts.append(f"- Annual CVaR: {cvar['annual_cvar']*100:.2f}%")
        context_parts.append("")
    
    # Risk contributions
    if risk_data['risk_contributions']:
        context_parts.append("## Risk Contribution by Holding")
        for contrib in risk_data['risk_contributions'][:5]:
            context_parts.append(
                f"- {contrib['symbol']}: Weight {contrib['weight']:.1f}%, "
                f"Risk Contribution {contrib['risk_contribution']:.1f}%"
            )
        context_parts.append("")
    
    # Correlation summary
    if not risk_data['correlation_matrix'].empty:
        corr_matrix = risk_data['correlation_matrix']
        avg_corr = corr_matrix.values[corr_matrix.values != 1].mean()
        context_parts.append("## Correlation Analysis")
        context_parts.append(f"- Average Correlation: {avg_corr:.3f}")
        context_parts.append(f"- Number of Stocks: {len(corr_matrix)}")
    
    return "\n".join(context_parts)

def get_system_prompt():
    """Get system prompt for portfolio advisor AI"""
    
    return """You are an expert Indian stock market portfolio advisor. You have access to detailed portfolio data including holdings, metrics, risk analysis, and optimization results.

Your role is to:
1. Provide clear, actionable insights about the portfolio
2. Explain complex financial metrics in simple terms
3. Identify risks and opportunities
4. Suggest improvements based on data
5. Answer questions about specific stocks, members, or the family portfolio
6. Use Indian Rupees (₹) when discussing values
7. Reference actual data from the portfolio context provided

Be concise, friendly, and focus on practical advice. When discussing risk, be balanced - acknowledge concerns without being alarmist. Always base your advice on the actual portfolio data provided in the context."""
