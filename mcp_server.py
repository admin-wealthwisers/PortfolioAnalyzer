"""
MCP Server for Portfolio Analytics
Exposes portfolio analysis tools to Claude via Model Context Protocol
"""

from mcp.server import Server
from mcp.types import Tool, TextContent
import json
import asyncio

# Import your existing modules
from portfolio.aggregator import process_portfolio_data
from portfolio.optimizer import optimize_family_portfolio
from portfolio.risk_analyzer import (
    analyze_portfolio_risk,
    simulate_scenarios,
    get_default_scenarios
)

# Create MCP server
server = Server("portfolio-analytics")


@server.tool()
async def analyze_portfolio(portfolio_json: str) -> str:
    """
    Analyze a family portfolio from JSON data.

    Calculates metrics, aggregates family/member data, detects overlaps.

    Args:
        portfolio_json: JSON string containing portfolio data with structure:
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

    Returns:
        JSON string with comprehensive portfolio analysis including:
        - Family-level metrics and aggregations
        - Individual member portfolios
        - Risk scores
        - Overlap detection
        - Performance metrics
    """
    try:
        data = json.loads(portfolio_json)
        result = process_portfolio_data(data)

        # Simplify for JSON serialization
        output = {
            "family": result['family'],
            "members": result['members'],
            "overlaps": result['overlaps'],
            "family_holdings": result['family_holdings']
        }

        return json.dumps(output, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@server.tool()
async def optimize_portfolio(
        portfolio_json: str,
        method: str = "max_sharpe"
) -> str:
    """
    Optimize portfolio allocation for better risk-adjusted returns.

    Args:
        portfolio_json: JSON string with portfolio data (same format as analyze_portfolio)
        method: Optimization method - one of:
            - "max_sharpe": Maximize Sharpe ratio (best risk-adjusted returns)
            - "min_volatility": Minimize portfolio volatility (lowest risk)
            - "equal_weight": Equal allocation across all stocks

    Returns:
        JSON string with:
        - Current portfolio metrics
        - Optimized portfolio metrics
        - Specific trade recommendations (buy/sell)
        - Expected improvements
        - Efficient frontier data
    """
    try:
        data = json.loads(portfolio_json)
        portfolio = process_portfolio_data(data)

        result = optimize_family_portfolio(portfolio, method=method)

        if result is None:
            return json.dumps({"error": "Optimization failed"})

        # Simplify for JSON
        output = {
            "current": result['current'],
            "optimized": result['optimized'],
            "improvement": result['improvement'],
            "trades": result['trades'][:10]  # Top 10 trades
        }

        return json.dumps(output, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@server.tool()
async def analyze_risk(portfolio_json: str) -> str:
    """
    Perform comprehensive risk analysis on portfolio.

    Calculates VaR, correlation, concentration risk, and risk contributions.

    Args:
        portfolio_json: JSON string with portfolio data

    Returns:
        JSON string with:
        - Value at Risk (VaR) and Conditional VaR
        - Correlation matrix between holdings
        - Concentration risk metrics (HHI, top holdings)
        - Risk contribution by holding
    """
    try:
        data = json.loads(portfolio_json)
        portfolio = process_portfolio_data(data)

        risk_data = analyze_portfolio_risk(portfolio)

        # Convert to JSON-serializable format
        output = {
            "concentration_risk": risk_data['concentration_risk'],
            "var": risk_data['var'],
            "cvar": risk_data['cvar'],
            "risk_contributions": risk_data['risk_contributions'][:5],  # Top 5
            "correlation_summary": {
                "avg_correlation": float(risk_data['correlation_matrix'].values[
                                             risk_data['correlation_matrix'].values != 1
                                             ].mean()) if not risk_data['correlation_matrix'].empty else 0
            }
        }

        return json.dumps(output, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@server.tool()
async def run_scenario(
        portfolio_json: str,
        scenario: str = "Market Crash (-20%)"
) -> str:
    """
    Run what-if scenario analysis on portfolio.

    Simulates how portfolio would perform under different market conditions.

    Args:
        portfolio_json: JSON string with portfolio data
        scenario: Scenario name - one of:
            - "Market Crash (-20%)": Overall market down 20%
            - "Market Rally (+15%)": Overall market up 15%
            - "Tech Selloff": Technology sector correction
            - "Banking Rally": Banking sector surge

    Returns:
        JSON string with:
        - Current portfolio value
        - Projected value under scenario
        - Value change (absolute and percentage)
        - Impact assessment
    """
    try:
        data = json.loads(portfolio_json)
        portfolio = process_portfolio_data(data)

        scenarios = get_default_scenarios()
        selected = next((s for s in scenarios if s['name'] == scenario), scenarios[0])

        results = simulate_scenarios(portfolio, [selected])

        if results:
            return json.dumps(results[0], indent=2)
        else:
            return json.dumps({"error": "Scenario simulation failed"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@server.tool()
async def get_stock_info(symbol: str) -> str:
    """
    Get detailed information about a specific stock.

    Args:
        symbol: Stock symbol (NSE format, e.g., "RELIANCE", "TCS")

    Returns:
        JSON string with stock metrics:
        - Current price
        - Volatility
        - Expected return
        - Sharpe ratio
        - Beta (vs Nifty 50)
    """
    try:
        from portfolio.calculator import calculate_stock_metrics

        metrics = calculate_stock_metrics(symbol)

        return json.dumps(metrics, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# Server startup
async def main():
    """Start the MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())