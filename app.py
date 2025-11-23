import gradio as gr
import json
import os
import subprocess
import atexit
from pathlib import Path
from portfolio.aggregator import process_portfolio_data
from portfolio.optimizer import optimize_family_portfolio, generate_efficient_frontier
from portfolio.risk_analyzer import analyze_portfolio_risk, simulate_scenarios, get_default_scenarios, \
    apply_scenario_to_all
from visualizations.charts import (
    create_family_treemap, create_member_treemap, create_allocation_pie,
    create_member_comparison_bar, create_holdings_table, create_overlap_chart,
    create_risk_indicator, create_efficient_frontier, create_weights_comparison,
    create_rebalancing_table, create_correlation_heatmap, create_risk_contribution_chart,
    create_scenario_comparison
)

try:
    from visualizations.pdf_report import generate_pdf_report

    PDF_AVAILABLE = True
except:
    PDF_AVAILABLE = False


    def generate_pdf_report(*args, **kwargs):
        return None

from llm.chat import get_chat_instance

# ========== MCP SERVER STARTUP ==========
try:
    mcp_process = subprocess.Popen(["python", "mcp_server.py"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
    atexit.register(mcp_process.terminate)
    MCP_AVAILABLE = True
    print("✅ MCP server started successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not start MCP server: {e}")
    MCP_AVAILABLE = False


# ========== MCP TOOL FUNCTIONS (Direct Import) ==========
def call_mcp_tool(tool_name, **kwargs):
    """Call MCP tool functions directly without client protocol"""
    try:
        # Import the actual MCP server functions
        from portfolio.aggregator import process_portfolio_data
        from portfolio.optimizer import optimize_family_portfolio
        from portfolio.risk_analyzer import analyze_portfolio_risk, simulate_scenarios, get_default_scenarios

        if 'portfolio_json' in kwargs:
            portfolio_data = json.loads(kwargs['portfolio_json'])
        else:
            return {"error": "No portfolio_json provided"}

        if tool_name == "analyze_portfolio":
            # Just return the portfolio data that's already processed
            return {
                "family": portfolio_data.get('family', {}),
                "members": portfolio_data.get('members', []),
                "overlaps": portfolio_data.get('overlaps', {}),
                "family_holdings": portfolio_data.get('family_holdings', {})
            }

        elif tool_name == "optimize_portfolio":
            method = kwargs.get('method', 'max_sharpe')
            result = optimize_family_portfolio(portfolio_data, method=method)
            if result:
                return {
                    "current": result['current'],
                    "optimized": result['optimized'],
                    "improvement": result['improvement'],
                    "trades": result['trades'][:10]
                }
            return {"error": "Optimization failed"}

        elif tool_name == "analyze_risk":
            risk_data = analyze_portfolio_risk(portfolio_data)
            return {
                "concentration_risk": risk_data['concentration_risk'],
                "var": risk_data['var'],
                "cvar": risk_data['cvar'],
                "risk_contributions": risk_data['risk_contributions'][:5]
            }

        elif tool_name == "run_scenario":
            scenario_name = kwargs.get('scenario', 'Market Crash (-20%)')
            scenarios = get_default_scenarios()
            for scenario in scenarios:
                if scenario['name'] == scenario_name:
                    all_symbols = list(portfolio_data['family_holdings'].keys())
                    scenario_map = {"Market Crash (-20%)": -20, "Market Rally (+15%)": 15}
                    default_change = scenario_map.get(scenario_name, 0)

                    # Apply scenario
                    from portfolio.risk_analyzer import apply_scenario_to_all
                    scenario = apply_scenario_to_all(scenario, all_symbols, default_change)
                    results = simulate_scenarios(portfolio_data, [scenario])

                    if results:
                        return results[0]
            return {"error": "Scenario not found"}

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ========== MCP QUICK ACTION HANDLER ==========
def handle_quick_action(action_name, portfolio_data, chat_history):
    """Handle MCP quick action buttons - returns dict format for Gradio Chatbot"""
    if chat_history is None:
        chat_history = []

    if not portfolio_data:
        response = "⚠️ Please analyze a portfolio first."
        return chat_history + [{"role": "user", "content": action_name}, {"role": "assistant", "content": response}]

    if not MCP_AVAILABLE:
        response = "⚠️ MCP server is not available."
        return chat_history + [{"role": "user", "content": action_name}, {"role": "assistant", "content": response}]

    try:
        portfolio_json = json.dumps(portfolio_data)

        if "Analyze" in action_name:
            result = call_mcp_tool("analyze_portfolio", portfolio_json=portfolio_json)
        elif "Optimize" in action_name:
            result = call_mcp_tool("optimize_portfolio", portfolio_json=portfolio_json, method="max_sharpe")
        elif "Risk" in action_name:
            result = call_mcp_tool("analyze_risk", portfolio_json=portfolio_json)
        elif "Scenario" in action_name:
            result = call_mcp_tool("run_scenario", portfolio_json=portfolio_json, scenario="Market Crash (-20%)")
        else:
            result = {"error": "Unknown action"}

        # Format response nicely
        response = json.dumps(result, indent=2)
        return chat_history + [{"role": "user", "content": action_name},
                               {"role": "assistant", "content": f"```json\n{response}\n```"}]

    except Exception as e:
        return chat_history + [{"role": "user", "content": action_name},
                               {"role": "assistant", "content": f"❌ Error: {str(e)}"}]


# ========== HARDCODED PORTFOLIO ==========
HARDCODED_JSON = {
    "email": "diversified.family@example.com",
    "investor": [
        {
            "id": "INV001",
            "name": "Arjun Kumar",
            "stocks": [
                {"symbol": "RELIANCE", "quantity": "20", "cost_basis": "2400.00"},
                {"symbol": "HDFCBANK", "quantity": "30", "cost_basis": "1600.00"},
                {"symbol": "ITC", "quantity": "100", "cost_basis": "420.00"},
                {"symbol": "SUNPHARMA", "quantity": "40", "cost_basis": "1520.00"},
                {"symbol": "MARUTI", "quantity": "5", "cost_basis": "11800.00"}
            ]
        },
        {
            "id": "INV002",
            "name": "Kavita Kumar",
            "stocks": [
                {"symbol": "TCS", "quantity": "25", "cost_basis": "3100.00"},
                {"symbol": "WIPRO", "quantity": "80", "cost_basis": "410.00"},
                {"symbol": "AXISBANK", "quantity": "50", "cost_basis": "1050.00"},
                {"symbol": "LT", "quantity": "15", "cost_basis": "3300.00"},
                {"symbol": "BHARTIARTL", "quantity": "60", "cost_basis": "780.00"}
            ]
        },
        {
            "id": "INV003",
            "name": "Rohan Kumar",
            "stocks": [
                {"symbol": "ICICIBANK", "quantity": "70", "cost_basis": "950.00"},
                {"symbol": "TATAMOTORS", "quantity": "100", "cost_basis": "850.00"},
                {"symbol": "HINDUNILVR", "quantity": "20", "cost_basis": "2300.00"},
                {"symbol": "SBIN", "quantity": "120", "cost_basis": "580.00"}
            ]
        }
    ]
}

portfolio_state = {}
charts_state = {}
optimization_state = {}
risk_state = {}


# ========== UI HELPER FUNCTIONS ==========
def create_metrics_bar_html(portfolio_data):
    family = portfolio_data['family']
    risk_score = family['risk_score']
    risk_class = 'gold' if risk_score < 6 else ''

    return f'''
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
                <div class="metric-subvalue">{'Low' if risk_score < 4 else 'Moderate' if risk_score < 7 else 'High'}</div>
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


def update_view(view_mode, member_name, portfolio_data):
    if not portfolio_data:
        return None, None, None

    if view_mode == "Family View":
        treemap = create_family_treemap(portfolio_data)
        member_comparison = create_member_comparison_bar(portfolio_data['members'])
        family_holdings_list = []
        for symbol, data in portfolio_data['family_holdings'].items():
            family_holdings_list.append({
                'symbol': symbol, 'quantity': data['quantity'],
                'current_price': portfolio_data['members'][0]['holdings'][0]['current_price'] if portfolio_data[
                    'members'] else 0,
                'value': data['value'], 'weight': data['weight'], 'gain_pct': 0
            })
        table = create_holdings_table(family_holdings_list)
        return treemap, member_comparison, table
    else:
        member_data = next((m for m in portfolio_data['members'] if m['name'] == member_name), None)
        if not member_data:
            return None, None, None
        treemap = create_member_treemap(member_data)
        pie_chart = create_allocation_pie(member_data['holdings'], f"{member_data['name']}'s Allocation")
        table = create_holdings_table(member_data['holdings'])
        return treemap, pie_chart, table


def toggle_member_dropdown(view_mode):
    return gr.update(visible=(view_mode == "Individual View"))


# ========== PORTFOLIO ANALYSIS FUNCTIONS ==========
def run_optimization(portfolio_data, method):
    if not portfolio_data:
        return "❌ No portfolio data", None, None, None, ""
    try:
        global optimization_state, charts_state
        method_map = {"Max Sharpe Ratio": "max_sharpe", "Min Volatility": "min_volatility",
                      "Equal Weight": "equal_weight"}
        result = optimize_family_portfolio(portfolio_data, method=method_map.get(method, "max_sharpe"))
        if not result:
            return "❌ Optimization failed", None, None, None, ""
        optimization_state['result'] = result
        all_symbols = list(portfolio_data['family_holdings'].keys())
        frontier = generate_efficient_frontier(all_symbols, n_points=30)
        frontier_plot = create_efficient_frontier(frontier, result['current'],
                                                  result['optimized']) if frontier else None
        weights_plot = create_weights_comparison(result['current']['weights'], result['optimized']['weights'])
        trades_table = create_rebalancing_table(result['trades'])
        charts_state.update({'efficient_frontier': frontier_plot, 'weights_comparison': weights_plot,
                             'rebalancing_table': trades_table})
        improvement = result['improvement']
        metrics_text = f"""### Optimization Results
**Current:** Return {result['current']['expected_return'] * 100:.2f}%, Vol {result['current']['volatility'] * 100:.2f}%, Sharpe {result['current']['sharpe_ratio']:.4f}
**Optimized:** Return {result['optimized']['expected_return'] * 100:.2f}%, Vol {result['optimized']['volatility'] * 100:.2f}%, Sharpe {result['optimized']['sharpe_ratio']:.4f}
**Improvements:** Return {improvement['return_change'] * 100:+.2f}%, Vol {improvement['volatility_change'] * 100:+.2f}%, Sharpe {improvement['sharpe_change']:+.4f}
**Trades Required:** {len(result['trades'])}"""
        return "✅ Optimization complete!", frontier_plot, weights_plot, trades_table, metrics_text
    except Exception as e:
        return f"❌ Error: {str(e)}", None, None, None, ""


def run_scenario_analysis(portfolio_data, scenario_name):
    if not portfolio_data:
        return None, "❌ No portfolio data"
    try:
        all_symbols = list(portfolio_data['family_holdings'].keys())
        scenarios = get_default_scenarios()
        scenario_map = {"Market Crash (-20%)": -20, "Market Rally (+15%)": 15, "Tech Selloff": 0, "Banking Rally": 0}
        default_change = scenario_map.get(scenario_name, 0)
        for scenario in scenarios:
            if scenario['name'] == scenario_name:
                scenario = apply_scenario_to_all(scenario, all_symbols, default_change)
                results = simulate_scenarios(portfolio_data, [scenario])
                if results:
                    result = results[0]
                    comparison_plot = create_scenario_comparison(results)
                    details = f"""### Scenario: {scenario_name}
**Current:** ₹{result['current_value']:,.2f}
**Projected:** ₹{result['scenario_value']:,.2f}
**Change:** ₹{result['value_change']:+,.2f} ({result['pct_change']:+.2f}%)
{"🔴 Portfolio would decrease" if result['pct_change'] < 0 else "🟢 Portfolio would increase"}"""
                    return comparison_plot, details
        return None, "❌ Scenario not found"
    except Exception as e:
        return None, f"❌ Error: {str(e)}"


def run_risk_analysis(portfolio_data):
    if not portfolio_data:
        return None, None, "", ""
    try:
        global risk_state, charts_state
        risk_data = analyze_portfolio_risk(portfolio_data)
        risk_state['data'] = risk_data
        corr_heatmap = create_correlation_heatmap(risk_data['correlation_matrix'])
        risk_contrib_chart = create_risk_contribution_chart(risk_data['risk_contributions'])
        charts_state.update({'correlation': corr_heatmap, 'risk_contribution': risk_contrib_chart})
        conc = risk_data['concentration_risk']
        conc_text = f"""### Concentration Risk
**HHI:** {conc['hhi']:.2f} | **Top 1:** {conc['top_1_concentration']:.1f}% | **Top 3:** {conc['top_3_concentration']:.1f}%
**Level:** {conc['concentration_level']} | **Rating:** {conc['risk_rating']}
**Effective Holdings:** {conc['effective_holdings']:.2f}"""
        var_text = ""
        if risk_data['var'] and risk_data['cvar']:
            var, cvar = risk_data['var'], risk_data['cvar']
            var_text = f"""### Value at Risk ({var['confidence_level'] * 100:.0f}%)
**Daily VaR:** {var['daily_var'] * 100:.2f}% | **Annual VaR:** {var['annual_var'] * 100:.2f}%
**Daily CVaR:** {cvar['daily_cvar'] * 100:.2f}% | **Annual CVaR:** {cvar['annual_cvar'] * 100:.2f}%"""
        else:
            var_text = "### Value at Risk\nInsufficient data"
        return corr_heatmap, risk_contrib_chart, conc_text, var_text
    except Exception as e:
        return None, None, f"❌ Error: {str(e)}", ""


def export_to_pdf(portfolio_data):
    if not PDF_AVAILABLE or not portfolio_data:
        return None, "❌ PDF export unavailable"
    try:
        global charts_state, optimization_state, risk_state
        output_path = f"/mnt/user-data/outputs/portfolio_report.pdf"
        pdf_path = generate_pdf_report(portfolio_data, charts_state, optimization_state.get('result'),
                                       risk_state.get('data'), output_path)
        return pdf_path, "✅ PDF generated!" if pdf_path else "❌ PDF generation failed"
    except Exception as e:
        return None, f"❌ Error: {str(e)}"


# ========== AI CHAT FUNCTIONS ==========
def refresh_suggested_questions(portfolio_data):
    if not portfolio_data:
        return gr.update(choices=["What is a good portfolio?", "How to diversify?", "What is Sharpe ratio?"])
    chat = get_chat_instance()
    return gr.update(choices=chat.get_suggested_questions(portfolio_data))


def send_chat(msg, history, portfolio_data, api_key):
    """Enhanced chat with MCP tool support"""
    if not msg:
        return history, ""
    if not history:
        history = []

    api_key = api_key if api_key and api_key.startswith("sk-ant-") else os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return history + [{"role": "user", "content": msg}, {"role": "assistant", "content": "⚠️ API key required"}], ""

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        # Define MCP tools for autonomous use
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

        # Build messages (extract from dict format history)
        messages = []
        for msg_dict in history:
            if isinstance(msg_dict, dict):
                if msg_dict.get('role') == 'user':
                    messages.append({"role": "user", "content": msg_dict.get('content', '')})
                elif msg_dict.get('role') == 'assistant':
                    messages.append({"role": "assistant", "content": msg_dict.get('content', '')})

        # Add current message
        messages.append({
            "role": "user",
            "content": f"{msg}\n\n[Portfolio data available]" if portfolio_data else msg
        })

        # Call Claude API with tools
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            tools=tools,
            messages=messages
        )

        # Handle tool use
        if response.stop_reason == "tool_use":
            tool_block = next((b for b in response.content if b.type == "tool_use"), None)

            if tool_block and portfolio_data and MCP_AVAILABLE:
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

                # Get final response
                final_response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=messages
                )

                response_text = "".join([b.text for b in final_response.content if hasattr(b, 'text')])
            else:
                response_text = "⚠️ Tools are not available. Please check MCP server."
        else:
            # Direct answer
            response_text = "".join([b.text for b in response.content if hasattr(b, 'text')])

        # Return in dict format for Gradio Chatbot
        return history + [{"role": "user", "content": msg}, {"role": "assistant", "content": response_text}], ""

    except Exception as e:
        import traceback
        traceback.print_exc()
        return history + [{"role": "user", "content": msg}, {"role": "assistant", "content": f"❌ Error: {str(e)}"}], ""


# ========== CSS ==========
CSS = """
:root {
    --primary-teal: #1a5e63;
    --primary-teal-light: #2d7f85;
    --accent-gold: #c8932e;
}
.metrics-bar {
    position: sticky;
    top: 0;
    z-index: 100;
    background: white;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-bottom: 3px solid var(--primary-teal);
    margin-bottom: 1rem;
}
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.5rem;
    max-width: 1400px;
    margin: 0 auto;
}
.metric-card {
    background: linear-gradient(135deg, var(--primary-teal) 0%, var(--primary-teal-light) 100%);
    color: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(26, 94, 99, 0.2);
}
.metric-card.gold {
    background: linear-gradient(135deg, var(--accent-gold) 0%, #d4a445 100%);
}
.metric-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    opacity: 0.9;
    margin-bottom: 0.25rem;
}
.metric-value {
    font-size: 1.75rem;
    font-weight: 700;
    margin: 0.25rem 0;
}
.metric-subvalue {
    font-size: 0.9rem;
    opacity: 0.85;
}
"""

# ========== GRADIO INTERFACE ==========
with gr.Blocks(title="Portfolio Analytics") as app:
    # Process hardcoded portfolio on startup
    portfolio_data = process_portfolio_data(HARDCODED_JSON)
    portfolio_state = portfolio_data

    # Load CSS inline
    gr.HTML(f"<style>{CSS}</style>")

    # Generate initial charts
    treemap = create_family_treemap(portfolio_data)
    member_comparison = create_member_comparison_bar(portfolio_data['members'])
    overlap_chart = create_overlap_chart(portfolio_data['overlaps'])
    risk_chart = create_risk_indicator(portfolio_data['family']['risk_score'])

    charts_state.update(
        {'treemap': treemap, 'member_comparison': member_comparison, 'overlap': overlap_chart, 'risk': risk_chart})

    # Header
    gr.HTML('<h1 style="text-align: center; color: #1a5e63;">📊 Portfolio Analytics Platform</h1>')
    gr.HTML(create_metrics_bar_html(portfolio_data))

    # State
    portfolio_data_state = gr.State(value=portfolio_data)

    # Main visualizations
    with gr.Row():
        with gr.Column():
            treemap_plot = gr.Plot(value=treemap, label="Portfolio Allocation")
        with gr.Column():
            comparison_plot = gr.Plot(value=member_comparison, label="Member Comparison")

    with gr.Row():
        with gr.Column():
            overlap_plot = gr.Plot(value=overlap_chart, label="Overlapping Holdings")
        with gr.Column():
            risk_plot = gr.Plot(value=risk_chart, label="Risk Score")

    holdings_table = gr.Plot(label="Holdings Details")

    # Tabs
    with gr.Tabs():
        with gr.TabItem("⚡ Optimization"):
            with gr.Row():
                opt_method = gr.Radio(["Max Sharpe Ratio", "Min Volatility", "Equal Weight"], value="Max Sharpe Ratio",
                                      label="Method")
                optimize_btn = gr.Button("Optimize", variant="primary")
            opt_status = gr.Markdown("")
            with gr.Row():
                frontier_plot = gr.Plot(label="Efficient Frontier")
                weights_plot = gr.Plot(label="Weights Comparison")
            rebal_table = gr.Plot(label="Rebalancing")
            metrics_comp = gr.Markdown("")

        with gr.TabItem("🔮 Scenarios"):
            with gr.Row():
                scenario_select = gr.Dropdown(
                    choices=["Market Crash (-20%)", "Market Rally (+15%)", "Tech Selloff", "Banking Rally"],
                    value="Market Crash (-20%)", label="Scenario")
                scenario_btn = gr.Button("Run", variant="primary")
            scenario_plot = gr.Plot(label="Impact")
            scenario_details = gr.Markdown("")

        with gr.TabItem("⚠️ Risk Analysis"):
            risk_btn = gr.Button("Analyze Risk", variant="primary")
            with gr.Row():
                corr_heatmap = gr.Plot(label="Correlation")
                risk_contrib = gr.Plot(label="Risk Contribution")
            with gr.Row():
                conc_metrics = gr.Markdown("")
                var_metrics = gr.Markdown("")

        with gr.TabItem("💬 AI Chat"):
            with gr.Row():
                api_key_input = gr.Textbox(label="API Key (optional)", type="password", scale=3)

            # MCP Quick Actions
            if MCP_AVAILABLE:
                gr.Markdown("#### 🚀 Quick Actions (MCP Tools)")
                with gr.Row():
                    mcp_analyze_btn = gr.Button("📊 Analyze", variant="secondary")
                    mcp_optimize_btn = gr.Button("⚡ Optimize", variant="secondary")
                    mcp_risk_btn = gr.Button("⚠️ Risk", variant="secondary")
                    mcp_scenario_btn = gr.Button("🔮 Scenario", variant="secondary")

            suggested = gr.Dropdown(choices=[], label="Suggested Questions")
            chatbot = gr.Chatbot(height=400)
            with gr.Row():
                msg_input = gr.Textbox(label="Ask", scale=4)
                send_btn = gr.Button("Send", variant="primary", scale=1)

    # PDF Export
    pdf_output = gr.File(visible=False)
    export_status = gr.Markdown("")
    export_btn = gr.Button("📥 Export PDF")

    # ========== EVENT HANDLERS ==========
    optimize_btn.click(run_optimization, [portfolio_data_state, opt_method],
                       [opt_status, frontier_plot, weights_plot, rebal_table, metrics_comp])
    scenario_btn.click(run_scenario_analysis, [portfolio_data_state, scenario_select],
                       [scenario_plot, scenario_details])
    risk_btn.click(run_risk_analysis, [portfolio_data_state], [corr_heatmap, risk_contrib, conc_metrics, var_metrics])

    export_btn.click(export_to_pdf, [portfolio_data_state], [pdf_output, export_status])

    # MCP Quick Actions
    if MCP_AVAILABLE:
        mcp_analyze_btn.click(
            lambda pd, ch: handle_quick_action("📊 Analyze", pd, ch),
            [portfolio_data_state, chatbot],
            [chatbot]
        )
        mcp_optimize_btn.click(
            lambda pd, ch: handle_quick_action("⚡ Optimize", pd, ch),
            [portfolio_data_state, chatbot],
            [chatbot]
        )
        mcp_risk_btn.click(
            lambda pd, ch: handle_quick_action("⚠️ Risk", pd, ch),
            [portfolio_data_state, chatbot],
            [chatbot]
        )
        mcp_scenario_btn.click(
            lambda pd, ch: handle_quick_action("🔮 Scenario", pd, ch),
            [portfolio_data_state, chatbot],
            [chatbot]
        )

    # Chat handlers
    send_btn.click(send_chat, [msg_input, chatbot, portfolio_data_state, api_key_input], [chatbot, msg_input])
    msg_input.submit(send_chat, [msg_input, chatbot, portfolio_data_state, api_key_input], [chatbot, msg_input])

    # Load suggested questions on startup
    app.load(lambda: refresh_suggested_questions(portfolio_data), outputs=[suggested])

if __name__ == "__main__":
    app.launch(server_name="127.0.0.1", server_port=7860)
