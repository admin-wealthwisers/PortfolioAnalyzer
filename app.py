import gradio as gr
import json
import os
import plotly.graph_objects as go
import subprocess
import atexit
import asyncio
from pathlib import Path
from utils.validators import validate_portfolio_json, sanitize_json_input
from portfolio.aggregator import process_portfolio_data
from portfolio.optimizer import (
    optimize_family_portfolio,
    generate_efficient_frontier
)
from portfolio.risk_analyzer import (
    analyze_portfolio_risk,
    simulate_scenarios,
    get_default_scenarios,
    apply_scenario_to_all
)
from visualizations.charts import (
    create_family_treemap,
    create_member_treemap,
    create_allocation_pie,
    create_member_comparison_bar,
    create_holdings_table,
    create_overlap_chart,
    create_risk_indicator,
    create_efficient_frontier,
    create_weights_comparison,
    create_rebalancing_table,
    create_correlation_heatmap,
    create_risk_contribution_chart,
    create_scenario_comparison
)

try:
    from visualizations.pdf_report import generate_pdf_report

    PDF_AVAILABLE = True
except (ImportError, OSError):
    PDF_AVAILABLE = False


    def generate_pdf_report(*args, **kwargs):
        return None

from llm.chat import get_chat_instance, send_message
from llm.context_builder import build_portfolio_context

# ========== CUSTOM CSS/JS LOADING ==========
STATIC_DIR = Path(__file__).parent / "static"
CUSTOM_CSS_PATH = STATIC_DIR / "custom.css"
CUSTOM_JS_PATH = STATIC_DIR / "custom.js"


def load_custom_css():
    if CUSTOM_CSS_PATH.exists():
        return CUSTOM_CSS_PATH.read_text(encoding='utf-8')  # ← Added encoding
    return ""

def load_custom_js():
    if CUSTOM_JS_PATH.exists():
        return f"<script>{CUSTOM_JS_PATH.read_text(encoding='utf-8')}</script>"  # ← Added encoding
    return ""


# Global state to store processed portfolio data
portfolio_state = {}
charts_state = {}
optimization_state = {}
risk_state = {}

# MCP Server startup
try:
    mcp_process = subprocess.Popen(["python", "mcp_server.py"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
    atexit.register(mcp_process.terminate)
    MCP_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not start MCP server: {e}")
    MCP_AVAILABLE = False


# ========== MCP CLIENT FUNCTIONS (UNCHANGED) ==========
async def call_mcp_tool_async(tool_name, **kwargs):
    """Call MCP tool asynchronously"""
    try:
        from mcp.client import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"]
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=kwargs)
                return json.loads(result.content[0].text)
    except Exception as e:
        return {"error": str(e)}


def call_mcp_tool(tool_name, **kwargs):
    """Synchronous wrapper for MCP tool calls"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(call_mcp_tool_async(tool_name, **kwargs))
        loop.close()
        return result
    except Exception as e:
        return {"error": str(e)}


def format_analysis_result(result):
    """Format analysis result for display"""
    if "error" in result:
        return f"❌ Error: {result['error']}"

    family = result.get('family', {})
    overlaps = result.get('overlaps', {})

    overlap_text = ""
    if overlaps:
        overlap_text = "\n\n⚠️ **Overlapping Holdings:**\n" + "\n".join(
            f"- {symbol}: {len(owners)} members ({', '.join(owners)})"
            for symbol, owners in overlaps.items()
        )
    else:
        overlap_text = "\n\n✅ No overlapping holdings detected"

    return f"""
📊 **Portfolio Analysis Complete**

**Total Value:** ₹{family.get('total_value', 0):,.2f}
**Total Gain:** ₹{family.get('total_gain', 0):,.2f} ({family.get('total_gain_pct', 0):.2f}%)
**Risk Score:** {family.get('risk_score', 0):.1f}/10
**Members:** {family.get('member_count', 0)}
**Unique Stocks:** {family.get('unique_stocks', 0)}

**Metrics:**
- Volatility: {family.get('metrics', {}).get('volatility', 0):.4f}
- Sharpe Ratio: {family.get('metrics', {}).get('sharpe_ratio', 0):.4f}
- Beta: {family.get('metrics', {}).get('beta', 0):.4f}
{overlap_text}
"""


def format_optimization_result(result):
    """Format optimization result"""
    if "error" in result:
        return f"❌ Error: {result['error']}"

    current = result.get('current', {})
    optimized = result.get('optimized', {})
    improvement = result.get('improvement', {})
    trades = result.get('trades', [])

    trades_text = "\n".join(
        f"{i + 1}. {t['action']} {t['quantity']:.0f} shares of {t['symbol']} (₹{t['value']:,.0f})"
        for i, t in enumerate(trades[:5])
    )

    return f"""
⚡ **Optimization Results**

**Current Portfolio:**
- Expected Return: {current.get('expected_return', 0) * 100:.2f}%
- Volatility: {current.get('volatility', 0) * 100:.2f}%
- Sharpe Ratio: {current.get('sharpe_ratio', 0):.4f}

**Optimized Portfolio:**
- Expected Return: {optimized.get('expected_return', 0) * 100:.2f}%
- Volatility: {optimized.get('volatility', 0) * 100:.2f}%
- Sharpe Ratio: {optimized.get('sharpe_ratio', 0):.4f}

**Improvements:**
- Return Change: {improvement.get('return_change', 0) * 100:+.2f}%
- Volatility Change: {improvement.get('volatility_change', 0) * 100:+.2f}%
- Sharpe Change: {improvement.get('sharpe_change', 0):+.4f}

**Top 5 Recommended Trades:**
{trades_text}

Total trades needed: {len(trades)}
"""


def format_risk_result(result):
    """Format risk result"""
    if "error" in result:
        return f"❌ Error: {result['error']}"

    conc = result.get('concentration_risk', {})
    var_data = result.get('var', {})
    cvar_data = result.get('cvar', {})

    var_text = ""
    if var_data:
        var_text = f"""
**Value at Risk ({var_data.get('confidence_level', 0.95) * 100:.0f}% confidence):**
- Daily VaR: {var_data.get('daily_var', 0) * 100:.2f}%
- Annual VaR: {var_data.get('annual_var', 0) * 100:.2f}%

**Conditional VaR (CVaR):**
- Daily CVaR: {cvar_data.get('daily_cvar', 0) * 100:.2f}%
- Annual CVaR: {cvar_data.get('annual_cvar', 0) * 100:.2f}%
"""

    return f"""
⚠️ **Risk Analysis**

**Concentration Risk:**
- Level: {conc.get('concentration_level', 'Unknown')}
- Rating: {conc.get('risk_rating', 'Unknown')}
- HHI Index: {conc.get('hhi', 0):.2f}

**Top Holdings Concentration:**
- Top 1 Stock: {conc.get('top_1_concentration', 0):.1f}%
- Top 3 Stocks: {conc.get('top_3_concentration', 0):.1f}%
- Top 5 Stocks: {conc.get('top_5_concentration', 0):.1f}%

{var_text}

**Effective Number of Holdings:** {conc.get('effective_holdings', 0):.2f}
"""


def format_scenario_result(result):
    """Format scenario result"""
    if "error" in result:
        return f"❌ Error: {result['error']}"

    return f"""
🔮 **Scenario: {result.get('scenario', 'Unknown')}**

**Current Value:** ₹{result.get('current_value', 0):,.2f}
**Projected Value:** ₹{result.get('scenario_value', 0):,.2f}
**Change:** ₹{result.get('value_change', 0):+,.2f} ({result.get('pct_change', 0):+.2f}%)

{"🔴 Portfolio would decrease in value" if result.get('pct_change', 0) < 0 else "🟢 Portfolio would increase in value"}
"""


def handle_quick_action(action_name, portfolio_data, chat_history):
    """Handle conversation starter buttons"""
    if chat_history is None:
        chat_history = []

    if not portfolio_data:
        response = "⚠️ **Please analyze a portfolio first.**\n\nUpload a JSON file or paste JSON data, then click the '🔍 Analyze Portfolio' button in the input section above."
        return chat_history + [{"role": "user", "content": action_name}, {"role": "assistant", "content": response}]

    if not MCP_AVAILABLE:
        response = "⚠️ MCP server is not available. Please ensure mcp_server.py is running."
        return chat_history + [{"role": "user", "content": action_name}, {"role": "assistant", "content": response}]

    try:
        portfolio_json = json.dumps(portfolio_data)

        if "Analyze" in action_name:
            result = call_mcp_tool("analyze_portfolio", portfolio_json=portfolio_json)
            response = format_analysis_result(result)
        elif "Optimize" in action_name:
            result = call_mcp_tool("optimize_portfolio", portfolio_json=portfolio_json, method="max_sharpe")
            response = format_optimization_result(result)
        elif "Risk" in action_name:
            result = call_mcp_tool("analyze_risk", portfolio_json=portfolio_json)
            response = format_risk_result(result)
        elif "Scenario" in action_name:
            result = call_mcp_tool("run_scenario", portfolio_json=portfolio_json, scenario="Market Crash (-20%)")
            response = format_scenario_result(result)
        else:
            response = "❌ Unknown action"

        return chat_history + [{"role": "user", "content": action_name}, {"role": "assistant", "content": response}]
    except Exception as e:
        import traceback
        traceback.print_exc()
        return chat_history + [{"role": "user", "content": action_name},
                               {"role": "assistant", "content": f"❌ Error: {str(e)}"}]


# ========== NEW UI HELPER FUNCTIONS ==========

def create_metrics_bar(portfolio_data):
    """Create sticky metrics bar with key KPIs"""
    if not portfolio_data:
        return gr.update(value="", visible=False)

    family = portfolio_data['family']
    risk_score = family['risk_score']

    # Color class based on risk
    risk_class = '' if risk_score >= 6 else 'gold'

    html = f'''
    <div class="metrics-bar">
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total Value</div>
                <div class="metric-value">₹{family['total_value'] / 100000:.2f}L</div>
                <div class="metric-subvalue">{family['total_gain_pct']:+.2f}%</div>
            </div>

            <div class="metric-card {risk_class}">
                <div class="metric-label">Risk Score</div>
                <div class="metric-value">{family['risk_score']:.1f}/10</div>
                <div class="metric-subvalue">
                    {'Low' if risk_score < 4 else 'Moderate' if risk_score < 7 else 'High'}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Diversification</div>
                <div class="metric-value">{family['metrics']['diversification_score']:.1f}/10</div>
                <div class="metric-subvalue">Sharpe: {family['metrics']['sharpe_ratio']:.2f}</div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Family Members</div>
                <div class="metric-value">{family['member_count']}</div>
                <div class="metric-subvalue">{family['unique_stocks']} stocks</div>
            </div>
        </div>
    </div>
    '''
    return gr.update(value=html, visible=True)


def generate_ai_insights(portfolio_data):
    """Generate AI insights based on portfolio analysis"""
    if not portfolio_data:
        return "Upload a portfolio to get AI-powered insights..."

    family = portfolio_data['family']
    overlaps = portfolio_data.get('overlaps', {})

    insights = []

    # Risk assessment
    if family['risk_score'] > 6:
        insights.append(
            "⚠️ **High Risk Alert**: Your portfolio has a risk score of {:.1f}/10. Consider diversifying to reduce volatility.".format(
                family['risk_score']))
    elif family['risk_score'] < 3:
        insights.append(
            "✅ **Conservative Portfolio**: Low risk score of {:.1f}/10. Good for stability, but returns may be limited.".format(
                family['risk_score']))
    else:
        insights.append(
            "📊 **Balanced Portfolio**: Moderate risk score of {:.1f}/10 indicates a good risk-reward balance.".format(
                family['risk_score']))

    # Diversification
    div_score = family['metrics']['diversification_score']
    if div_score < 5:
        insights.append(
            "🌈 **Low Diversification**: Score of {:.1f}/10. Add more stocks across different sectors.".format(
                div_score))
    elif div_score > 7:
        insights.append("🌟 **Well Diversified**: Excellent diversification score of {:.1f}/10!".format(div_score))

    # Overlaps
    if overlaps:
        insights.append(
            "⚠️ **Overlap Alert**: {} stocks held by multiple family members. This concentrates risk.".format(
                len(overlaps)))

    # Performance
    if family['total_gain_pct'] > 15:
        insights.append("🎉 **Strong Performance**: Portfolio up {:.1f}%! Consider rebalancing to lock in gains.".format(
            family['total_gain_pct']))
    elif family['total_gain_pct'] < -5:
        insights.append(
            "📉 **Underperforming**: Portfolio down {:.1f}%. Review holdings and consider optimization.".format(
                family['total_gain_pct']))

    return "\n\n".join(insights) if insights else "Your portfolio looks balanced. Continue monitoring regularly!"


# ========== ENHANCED PROCESS INPUT ==========

def process_input(file_input, json_text, input_method):
    """Enhanced: Process portfolio input and manage UI states"""
    try:
        # Get JSON data based on input method
        if input_method == "Upload JSON" and file_input is not None:
            json_data = json.load(open(file_input.name, 'r'))
        elif input_method == "Paste JSON" and json_text:
            json_data = json.loads(json_text)
        else:
            return (
                "❌ Please provide portfolio data",
                None, None, None, None,
                gr.update(choices=[], visible=False),
                None,
                gr.update(visible=True),  # Keep empty state visible
                gr.update(visible=False),  # Hide results state
                gr.update(value="", visible=False),  # Hide metrics bar
                ""  # AI insights
            )

        # Validate
        is_valid, message = validate_portfolio_json(json_data)
        if not is_valid:
            return (
                f"❌ Validation Error: {message}",
                None, None, None, None,
                gr.update(choices=[], visible=False),
                None,
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(value="", visible=False),
                ""
            )

        # Sanitize and process
        sanitized_data = sanitize_json_input(json_data)
        result = process_portfolio_data(sanitized_data)

        # Store in global state
        global portfolio_state, charts_state
        portfolio_state = result

        # Generate summary message
        family = result['family']
        summary = f"""
## ✅ Portfolio Analyzed Successfully

**{family['email']}** - {family['member_count']} members, {family['unique_stocks']} unique stocks

All visualizations are now available below. Click the 🔄 icon on any chart to learn more about that metric.
"""

        # Create visualizations
        treemap = create_family_treemap(result)
        member_comparison = create_member_comparison_bar(result['members'])
        overlap_chart = create_overlap_chart(result['overlaps'])
        risk_chart = create_risk_indicator(family['risk_score'])

        # Store charts for PDF export
        charts_state['treemap'] = treemap
        charts_state['member_comparison'] = member_comparison
        charts_state['overlap'] = overlap_chart
        charts_state['risk'] = risk_chart

        # Create member dropdown options
        member_names = [m['name'] for m in result['members']]

        # Generate AI insights
        ai_insights = generate_ai_insights(result)

        return (
            summary,
            treemap,
            member_comparison,
            overlap_chart,
            risk_chart,
            gr.update(choices=member_names, value=member_names[0], visible=True),
            result,
            gr.update(visible=False),  # Hide empty state
            gr.update(visible=True),  # Show results state
            create_metrics_bar(result),  # Show metrics bar
            ai_insights
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return (
            f"❌ Error: {str(e)}",
            None, None, None, None,
            gr.update(choices=[], visible=False),
            None,
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(value="", visible=False),
            ""
        )


# ========== ORIGINAL FUNCTIONS (UNCHANGED) ==========

def update_view(view_mode, member_name, portfolio_data):
    """Update visualizations based on view mode"""
    if not portfolio_data:
        return None, None, None

    if view_mode == "Family View":
        treemap = create_family_treemap(portfolio_data)
        member_comparison = create_member_comparison_bar(portfolio_data['members'])

        # Create aggregated holdings table
        family_holdings_list = []
        for symbol, data in portfolio_data['family_holdings'].items():
            family_holdings_list.append({
                'symbol': symbol,
                'quantity': data['quantity'],
                'current_price': portfolio_data['members'][0]['holdings'][0]['current_price'] if portfolio_data[
                    'members'] else 0,
                'value': data['value'],
                'weight': data['weight'],
                'gain_pct': 0  # Family level doesn't track individual gains
            })

        table = create_holdings_table(family_holdings_list)

        return treemap, member_comparison, table

    else:  # Individual View
        # Find the member
        member_data = None
        for member in portfolio_data['members']:
            if member['name'] == member_name:
                member_data = member
                break

        if not member_data:
            return None, None, None

        # Create member-specific visualizations
        treemap = create_member_treemap(member_data)
        pie_chart = create_allocation_pie(member_data['holdings'], f"{member_data['name']}'s Allocation")
        table = create_holdings_table(member_data['holdings'])

        return treemap, pie_chart, table


def toggle_member_dropdown(view_mode):
    """Show/hide member dropdown based on view mode"""
    return gr.update(visible=(view_mode == "Individual View"))


def run_optimization(portfolio_data, method):
    """Run portfolio optimization"""
    if not portfolio_data:
        return "❌ Please analyze a portfolio first", None, None, None, ""

    try:
        global optimization_state, charts_state

        # Map UI method names to function parameters
        method_map = {
            "Max Sharpe Ratio": "max_sharpe",
            "Min Volatility": "min_volatility",
            "Equal Weight": "equal_weight"
        }

        opt_method = method_map.get(method, "max_sharpe")

        # Run optimization
        result = optimize_family_portfolio(portfolio_data, method=opt_method)

        if result is None:
            return "❌ Optimization failed. Please try again.", None, None, None, ""

        # Store in global state
        optimization_state['result'] = result

        # Generate efficient frontier
        all_symbols = list(portfolio_data['family_holdings'].keys())
        frontier = generate_efficient_frontier(all_symbols, n_points=30)

        # Create visualizations
        if frontier:
            frontier_plot = create_efficient_frontier(
                frontier,
                current_point=result['current'],
                optimal_point=result['optimized']
            )
            charts_state['efficient_frontier'] = frontier_plot
        else:
            frontier_plot = None

        weights_plot = create_weights_comparison(
            result['current']['weights'],
            result['optimized']['weights']
        )
        charts_state['weights_comparison'] = weights_plot

        trades_table = create_rebalancing_table(result['trades'])
        charts_state['rebalancing_table'] = trades_table

        # Create metrics comparison
        improvement = result['improvement']
        metrics_text = f"""
### Optimization Results

**Current Portfolio:**
- Expected Return: {result['current']['expected_return'] * 100:.2f}%
- Volatility: {result['current']['volatility'] * 100:.2f}%
- Sharpe Ratio: {result['current']['sharpe_ratio']:.4f}

**Optimized Portfolio:**
- Expected Return: {result['optimized']['expected_return'] * 100:.2f}%
- Volatility: {result['optimized']['volatility'] * 100:.2f}%
- Sharpe Ratio: {result['optimized']['sharpe_ratio']:.4f}

**Improvements:**
- Return Change: {improvement['return_change'] * 100:+.2f}%
- Volatility Change: {improvement['volatility_change'] * 100:+.2f}%
- Sharpe Change: {improvement['sharpe_change']:+.4f}

**Trades Required:** {len(result['trades'])} rebalancing actions
"""

        status = "✅ Optimization complete! See results below."

        return status, frontier_plot, weights_plot, trades_table, metrics_text

    except Exception as e:
        return f"❌ Error during optimization: {str(e)}", None, None, None, ""


def run_scenario_analysis(portfolio_data, scenario_name):
    """Run scenario analysis"""
    if not portfolio_data:
        return None, "❌ Please analyze a portfolio first"

    try:
        # Get all symbols
        all_symbols = list(portfolio_data['family_holdings'].keys())

        # Get scenarios
        scenarios = get_default_scenarios()

        # Apply default changes to all stocks
        scenario_map = {
            "Market Crash (-20%)": -20,
            "Market Rally (+15%)": 15,
            "Tech Selloff": 0,
            "Banking Rally": 0
        }

        default_change = scenario_map.get(scenario_name, 0)

        # Find and apply the selected scenario
        for scenario in scenarios:
            if scenario['name'] == scenario_name:
                scenario = apply_scenario_to_all(scenario, all_symbols, default_change)
                results = simulate_scenarios(portfolio_data, [scenario])

                if results:
                    result = results[0]

                    # Create comparison chart
                    comparison_plot = create_scenario_comparison(results)

                    # Generate details
                    details_text = f"""
### Scenario: {scenario_name}

**Current Portfolio Value:** ₹{result['current_value']:,.2f}

**Projected Value:** ₹{result['scenario_value']:,.2f}

**Change:** ₹{result['value_change']:+,.2f} ({result['pct_change']:+.2f}%)

{"🔴 **Portfolio would decrease in value**" if result['pct_change'] < 0 else "🟢 **Portfolio would increase in value**"}
"""

                    return comparison_plot, details_text

        return None, "❌ Scenario not found"

    except Exception as e:
        return None, f"❌ Error: {str(e)}"


def run_risk_analysis(portfolio_data):
    """Run comprehensive risk analysis"""
    if not portfolio_data:
        return None, None, "", ""

    try:
        global risk_state, charts_state

        # Analyze risk
        risk_data = analyze_portfolio_risk(portfolio_data)

        # Store in global state
        risk_state['data'] = risk_data

        # Create visualizations
        corr_heatmap = create_correlation_heatmap(risk_data['correlation_matrix'])
        risk_contrib_chart = create_risk_contribution_chart(risk_data['risk_contributions'])

        # Store charts
        charts_state['correlation'] = corr_heatmap
        charts_state['risk_contribution'] = risk_contrib_chart

        # Concentration metrics
        conc = risk_data['concentration_risk']
        concentration_text = f"""
### Concentration Risk

**HHI Index:** {conc['hhi']:.2f}

**Top Holdings:**
- Top 1 Stock: {conc['top_1_concentration']:.1f}%
- Top 3 Stocks: {conc['top_3_concentration']:.1f}%
- Top 5 Stocks: {conc['top_5_concentration']:.1f}%

**Risk Level:** {conc['concentration_level']}  
**Rating:** {conc['risk_rating']}

**Effective Number of Holdings:** {conc['effective_holdings']:.2f}
"""

        # VaR metrics
        var_text = ""
        if risk_data['var'] and risk_data['cvar']:
            var = risk_data['var']
            cvar = risk_data['cvar']

            var_text = f"""
### Value at Risk (VaR)

**{var['confidence_level'] * 100:.0f}% Confidence Level:**

**Daily VaR:** {var['daily_var'] * 100:.2f}%  
**Annual VaR:** {var['annual_var'] * 100:.2f}%

**Conditional VaR (CVaR):**
- Daily: {cvar['daily_cvar'] * 100:.2f}%
- Annual: {cvar['annual_cvar'] * 100:.2f}%

*VaR represents the maximum expected loss at the given confidence level.*
"""
        else:
            var_text = "### Value at Risk\nInsufficient data for VaR calculation"

        return corr_heatmap, risk_contrib_chart, concentration_text, var_text

    except Exception as e:
        return None, None, f"❌ Error: {str(e)}", ""


# AI Chat functions
def set_api_key(api_key):
    """Set API key for chat"""
    if api_key and api_key.startswith("sk-ant-"):
        chat = get_chat_instance(api_key)
        return "✅ API key set successfully!"
    elif api_key:
        return "⚠️ Invalid API key format. Should start with 'sk-ant-'"
    else:
        return "ℹ️ Using environment variable for API key"


def refresh_suggested_questions_fn(portfolio_data):
    """Generate suggested questions based on current portfolio"""
    if not portfolio_data:
        return gr.update(choices=[
            "What should I consider when building a portfolio?",
            "How do I diversify my investments?",
            "What is a good Sharpe ratio?"
        ])

    chat = get_chat_instance()
    suggestions = chat.get_suggested_questions(portfolio_data)
    return gr.update(choices=suggestions)


def send_chat_message(user_message, chat_history, portfolio_data, api_key_input):
    if not user_message or not user_message.strip():
        return chat_history, ""

    if chat_history is None:
        chat_history = []

    api_key = api_key_input if api_key_input and api_key_input.startswith("sk-ant-") else os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        return (chat_history or []) + [(user_message, "⚠️ API key required")], ""

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        # Define tools
        tools = [
            {
                "name": "analyze_portfolio",
                "description": "Analyze family portfolio metrics, performance, and overlaps",
                "input_schema": {
                    "type": "object",
                    "properties": {"portfolio_json": {"type": "string"}},
                    "required": ["portfolio_json"]
                }
            },
            {
                "name": "optimize_portfolio",
                "description": "Optimize portfolio allocation for better returns",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_json": {"type": "string"},
                        "method": {"type": "string", "enum": ["max_sharpe", "min_volatility", "equal_weight"],
                                   "default": "max_sharpe"}
                    },
                    "required": ["portfolio_json"]
                }
            },
            {
                "name": "analyze_risk",
                "description": "Analyze portfolio risk metrics including VaR and concentration",
                "input_schema": {
                    "type": "object",
                    "properties": {"portfolio_json": {"type": "string"}},
                    "required": ["portfolio_json"]
                }
            },
            {
                "name": "run_scenario",
                "description": "Run what-if scenario analysis on portfolio",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_json": {"type": "string"},
                        "scenario": {"type": "string", "default": "Market Crash (-20%)"}
                    },
                    "required": ["portfolio_json"]
                }
            }
        ]

        # Build messages correctly
        messages = []

        # Add chat history
        if chat_history:
            for user_msg, assistant_msg in chat_history:
                if user_msg:
                    messages.append({"role": "user", "content": str(user_msg)})
                if assistant_msg:
                    messages.append({"role": "assistant", "content": str(assistant_msg)})

        # Add current message with context
        if portfolio_data:
            messages.append({
                "role": "user",
                "content": f"{user_message}\n\n[Portfolio data is available for analysis]"
            })
        else:
            messages.append({"role": "user", "content": user_message})

        # Call Claude
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            tools=tools,
            messages=messages
        )

        # Handle tool use
        if response.stop_reason == "tool_use":
            tool_block = next((b for b in response.content if b.type == "tool_use"), None)

            if tool_block and portfolio_data:
                # Call MCP tool
                tool_input = dict(tool_block.input)
                tool_input['portfolio_json'] = json.dumps(portfolio_data)

                mcp_result = call_mcp_tool(tool_block.name, **tool_input)

                # Continue conversation with tool result
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": json.dumps(mcp_result)
                    }]
                })

                final_response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=messages
                )

                response_text = "".join([b.text for b in final_response.content if hasattr(b, 'text')])
            else:
                response_text = "⚠️ Please analyze a portfolio first to use portfolio tools."
        else:
            # Direct answer
            response_text = "".join([b.text for b in response.content if hasattr(b, 'text')])

        return chat_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": response_text}
        ], ""

    except Exception as e:
        return (chat_history or []) + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": f"❌ Error: {str(e)}"}
        ], ""


def use_suggested_question(question, chat_history, portfolio_data, api_key_input):
    if question:
        return send_chat_message(question, chat_history, portfolio_data, api_key_input)
    return chat_history if chat_history else [], ""


def clear_chat_history():
    chat = get_chat_instance()
    chat.reset_conversation()
    return []


def update_chat_context(portfolio_data):
    """Update portfolio context in chat"""
    if portfolio_data:
        chat = get_chat_instance()
        chat.set_portfolio_data(portfolio_data)
        return "✅ Portfolio context updated in chat"
    return "⚠️ No portfolio data to update"


def export_to_pdf(portfolio_data):
    if not PDF_AVAILABLE:
        return None, "❌ PDF export not available. Install GTK: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases"

    global charts_state, optimization_state, risk_state

    if not portfolio_data:
        return None, "❌ No portfolio data to export. Please analyze a portfolio first."

    try:
        # Generate output filename
        family_email = portfolio_data['family']['email'].split('@')[0]
        output_path = f"/mnt/user-data/outputs/portfolio_report_{family_email}.pdf"

        # Generate PDF
        pdf_path = generate_pdf_report(
            portfolio_data,
            charts_dict=charts_state,
            optimization_result=optimization_state.get('result'),
            risk_data=risk_state.get('data'),
            output_path=output_path
        )

        if pdf_path:
            return pdf_path, f"✅ PDF report generated successfully!"
        else:
            return None, "❌ Failed to generate PDF. Please check if weasyprint is installed."

    except Exception as e:
        return None, f"❌ Error generating PDF: {str(e)}"


# ========== GRADIO INTERFACE WITH ENHANCED UI ==========

# Custom theme
custom_theme = gr.themes.Soft(
    primary_hue="cyan",
    secondary_hue="orange",
).set(
    button_primary_background_fill="#1a5e63",
    button_primary_background_fill_hover="#2d7f85",
)

# Create Gradio Interface
with gr.Blocks(
        title="Portfolio Analytics Platform",
        theme=custom_theme,
        css=load_custom_css(),
        head=load_custom_js()
) as app:
    # Store portfolio data
    portfolio_data_state = gr.State(value=None)

    # ========== HEADER ==========
    gr.HTML('''
    <div style="text-align: center; padding: 2rem 0 1rem 0;">
        <h1 style="color: #1a5e63; font-size: 2.5rem; margin-bottom: 0.5rem; font-weight: 700;">
            📊 Portfolio Analytics Platform
        </h1>
        <p style="color: #64748b; font-size: 1.1rem;">
            AI-powered insights for family portfolio management
        </p>
    </div>
    ''')

    # ========== EMPTY STATE (Initial View) ==========
    with gr.Group(visible=True, elem_id="empty-state") as empty_state:
        gr.HTML('''
        <div style="max-width: 800px; margin: 2rem auto; text-align: center; background: white; padding: 3rem; border-radius: 16px; box-shadow: 0 10px 40px rgba(26, 94, 99, 0.1);">
            <div style="font-size: 4rem; margin-bottom: 1rem;">💼</div>
            <h2 style="color: #1a5e63; font-size: 2rem; margin-bottom: 1rem;">Let's Analyze Your Portfolio</h2>
            <p style="color: #64748b; font-size: 1.1rem; margin-bottom: 2rem;">
                Upload your portfolio data to get started with AI-powered insights,
                risk analysis, and optimization recommendations.
            </p>
        </div>
        ''')

        with gr.Row():
            input_method = gr.Radio(
                ["Upload JSON", "Paste JSON"],
                value="Upload JSON",
                label="Input Method"
            )

        with gr.Row():
            with gr.Column(scale=1):
                file_upload = gr.File(label="📤 Upload Portfolio JSON", file_types=[".json"])
            with gr.Column(scale=1):
                json_text = gr.Textbox(
                    label="📋 Or Paste JSON Here",
                    lines=8,
                    placeholder='{"email": "family@example.com", "investor": [...]}'
                )

        analyze_btn = gr.Button(
            "🔍 Analyze Portfolio",
            variant="primary",
            size="lg"
        )

    # ========== RESULTS STATE (After Analysis) ==========
    with gr.Group(visible=False, elem_id="results-state") as results_state:

        # Sticky Metrics Bar
        metrics_bar = gr.HTML(value="", visible=False)

        # Top Action Bar
        with gr.Row():
            back_btn = gr.Button("← Back to Input", size="sm", variant="secondary")
            gr.HTML('<div style="flex-grow: 1;"></div>')
            export_btn = gr.Button("📥 Export PDF", size="sm", variant="secondary")

        analysis_status = gr.Markdown("")

        # View Toggle
        with gr.Row():
            view_mode = gr.Radio(
                ["Family View", "Individual View"],
                value="Family View",
                label="View Mode"
            )
            member_dropdown = gr.Dropdown(
                label="Select Member",
                visible=False
            )

        # Main Content Grid
        with gr.Row():
            # LEFT: Charts (60%)
            with gr.Column(scale=3):
                treemap_chart = gr.Plot(label="📊 Portfolio Allocation (Click to explore)")

                with gr.Row():
                    with gr.Column():
                        comparison_chart = gr.Plot(label="👥 Member Comparison")
                    with gr.Column():
                        risk_chart = gr.Plot(label="⚠️ Risk Score")

            # RIGHT: AI Insights (40%)
            with gr.Column(scale=2):
                with gr.Group(elem_id="ai-insights-card") as ai_insights:
                    gr.HTML('<h3 style="color: #c8932e; margin-bottom: 1rem;">💡 AI Insights</h3>')

                    ai_insights_content = gr.Markdown(
                        "Analyzing your portfolio...",
                        elem_classes="ai-insights-content"
                    )

        # Overlap chart (full width)
        overlap_chart = gr.Plot(label="🔗 Overlapping Holdings")

        # Holdings table
        holdings_table = gr.Plot(label="📋 Holdings Details")

        # Tabs for additional analysis
        with gr.Tabs():
            with gr.TabItem("⚡ Optimization"):
                gr.Markdown("### Portfolio Optimization")

                with gr.Row():
                    opt_method = gr.Radio(
                        ["Max Sharpe Ratio", "Min Volatility", "Equal Weight"],
                        value="Max Sharpe Ratio",
                        label="Optimization Method"
                    )
                    optimize_btn = gr.Button("🔄 Optimize Portfolio", variant="primary")

                optimization_status = gr.Markdown("")

                with gr.Row():
                    with gr.Column():
                        efficient_frontier_plot = gr.Plot(label="Efficient Frontier")
                    with gr.Column():
                        weights_comparison_plot = gr.Plot(label="Current vs Optimized Weights")

                rebalancing_table = gr.Plot(label="Rebalancing Recommendations")
                metrics_comparison = gr.Markdown("")

            with gr.TabItem("🔮 Scenarios"):
                gr.Markdown("### What-If Scenario Analysis")

                with gr.Row():
                    scenario_select = gr.Dropdown(
                        choices=[
                            "Market Crash (-20%)",
                            "Market Rally (+15%)",
                            "Tech Selloff",
                            "Banking Rally"
                        ],
                        value="Market Crash (-20%)",
                        label="Select Scenario"
                    )
                    run_scenario_btn = gr.Button("▶️ Run Scenario", variant="primary")

                scenario_results_plot = gr.Plot(label="Scenario Impact")
                scenario_details = gr.Markdown("")

            with gr.TabItem("⚠️ Risk Analysis"):
                gr.Markdown("### Comprehensive Risk Analysis")

                analyze_risk_btn = gr.Button("📊 Analyze Risk", variant="primary")

                with gr.Row():
                    with gr.Column():
                        correlation_heatmap = gr.Plot(label="Correlation Matrix")
                    with gr.Column():
                        risk_contribution_plot = gr.Plot(label="Risk Contribution")

                with gr.Row():
                    concentration_metrics = gr.Markdown("")
                    var_metrics = gr.Markdown("")

            with gr.TabItem("💬 Ask AI"):
                gr.Markdown("### AI Portfolio Advisor")

                with gr.Row():
                    api_key_input = gr.Textbox(
                        label="Anthropic API Key (Optional)",
                        placeholder="sk-ant-...",
                        type="password",
                        scale=3
                    )
                    set_api_key_btn = gr.Button("Set API Key", scale=1)

                api_status = gr.Markdown("ℹ️ Using environment variable for API key")

                # MCP Quick Actions
                if MCP_AVAILABLE:
                    gr.Markdown("#### 🚀 Quick Actions")
                    with gr.Row():
                        mcp_analyze_btn = gr.Button("📊 Analyze", variant="secondary")
                        mcp_optimize_btn = gr.Button("⚡ Optimize", variant="secondary")
                        mcp_risk_btn = gr.Button("⚠️ Risk", variant="secondary")
                        mcp_scenario_btn = gr.Button("🔮 Scenario", variant="secondary")

                with gr.Row():
                    suggested_questions = gr.Dropdown(
                        label="Suggested Questions",
                        choices=[],
                        interactive=True
                    )
                    refresh_suggestions_btn = gr.Button("🔄 Refresh", scale=0)

                chatbot = gr.Chatbot(
                    label="Portfolio Advisor Chat",
                    height=500
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        label="Your Question",
                        placeholder="Ask me anything about your portfolio...",
                        scale=4
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)

                with gr.Row():
                    clear_chat_btn = gr.Button("🗑️ Clear Chat")
                    update_context_btn = gr.Button("🔄 Update Context")

    # PDF Export Output
    pdf_output = gr.File(label="Download PDF Report", visible=False)
    export_status = gr.Markdown("")

    # ========== EVENT HANDLERS ==========

    # Main analyze button
    analyze_btn.click(
        fn=process_input,
        inputs=[file_upload, json_text, input_method],
        outputs=[
            analysis_status,
            treemap_chart,
            comparison_chart,
            overlap_chart,
            risk_chart,
            member_dropdown,
            portfolio_data_state,
            empty_state,
            results_state,
            metrics_bar,
            ai_insights_content
        ]
    ).then(
        fn=refresh_suggested_questions_fn,
        inputs=[portfolio_data_state],
        outputs=[suggested_questions]
    )

    # Back button
    back_btn.click(
        fn=lambda: (gr.update(visible=True), gr.update(visible=False)),
        outputs=[empty_state, results_state]
    )

    # View mode changes
    view_mode.change(
        fn=toggle_member_dropdown,
        inputs=[view_mode],
        outputs=[member_dropdown]
    )

    view_mode.change(
        fn=update_view,
        inputs=[view_mode, member_dropdown, portfolio_data_state],
        outputs=[treemap_chart, comparison_chart, holdings_table]
    )

    member_dropdown.change(
        fn=update_view,
        inputs=[view_mode, member_dropdown, portfolio_data_state],
        outputs=[treemap_chart, comparison_chart, holdings_table]
    )

    # Optimization tab
    optimize_btn.click(
        fn=run_optimization,
        inputs=[portfolio_data_state, opt_method],
        outputs=[
            optimization_status,
            efficient_frontier_plot,
            weights_comparison_plot,
            rebalancing_table,
            metrics_comparison
        ]
    )

    # Scenarios tab
    run_scenario_btn.click(
        fn=run_scenario_analysis,
        inputs=[portfolio_data_state, scenario_select],
        outputs=[scenario_results_plot, scenario_details]
    )

    # Risk Analysis tab
    analyze_risk_btn.click(
        fn=run_risk_analysis,
        inputs=[portfolio_data_state],
        outputs=[
            correlation_heatmap,
            risk_contribution_plot,
            concentration_metrics,
            var_metrics
        ]
    )

    # PDF Export
    export_btn.click(
        fn=export_to_pdf,
        inputs=[portfolio_data_state],
        outputs=[pdf_output, export_status]
    ).then(
        fn=lambda x: gr.update(visible=True) if x else gr.update(visible=False),
        inputs=[pdf_output],
        outputs=[pdf_output]
    )

    # AI Chat handlers
    set_api_key_btn.click(
        fn=set_api_key,
        inputs=[api_key_input],
        outputs=[api_status]
    )

    if MCP_AVAILABLE:
        mcp_analyze_btn.click(
            fn=lambda pd, ch: handle_quick_action("📊 Analyze Portfolio", pd, ch),
            inputs=[portfolio_data_state, chatbot],
            outputs=[chatbot]
        )

        mcp_optimize_btn.click(
            fn=lambda pd, ch: handle_quick_action("⚡ Optimize Portfolio", pd, ch),
            inputs=[portfolio_data_state, chatbot],
            outputs=[chatbot]
        )

        mcp_risk_btn.click(
            fn=lambda pd, ch: handle_quick_action("⚠️ Check Risk", pd, ch),
            inputs=[portfolio_data_state, chatbot],
            outputs=[chatbot]
        )

        mcp_scenario_btn.click(
            fn=lambda pd, ch: handle_quick_action("🔮 Run Scenario", pd, ch),
            inputs=[portfolio_data_state, chatbot],
            outputs=[chatbot]
        )

    refresh_suggestions_btn.click(
        fn=refresh_suggested_questions_fn,
        inputs=[portfolio_data_state],
        outputs=[suggested_questions]
    )

    send_btn.click(
        fn=send_chat_message,
        inputs=[msg_input, chatbot, portfolio_data_state, api_key_input],
        outputs=[chatbot, msg_input]
    )

    msg_input.submit(
        fn=send_chat_message,
        inputs=[msg_input, chatbot, portfolio_data_state, api_key_input],
        outputs=[chatbot, msg_input]
    )

    suggested_questions.change(
        fn=use_suggested_question,
        inputs=[suggested_questions, chatbot, portfolio_data_state, api_key_input],
        outputs=[chatbot, msg_input]
    )

    clear_chat_btn.click(
        fn=clear_chat_history,
        outputs=[chatbot]
    )

    update_context_btn.click(
        fn=update_chat_context,
        inputs=[portfolio_data_state],
        outputs=[api_status]
    )

if __name__ == "__main__":
    app.launch(share=False, server_name="0.0.0.0", server_port=7860)