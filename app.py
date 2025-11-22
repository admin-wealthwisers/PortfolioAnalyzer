import gradio as gr
import json
import os
import plotly.graph_objects as go
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

# Global state to store processed portfolio data
portfolio_state = {}
charts_state = {}
optimization_state = {}
risk_state = {}

def process_input(file_input, json_text, input_method):
    """Process portfolio input from file or text"""
    try:
        # Get JSON data based on input method
        if input_method == "Upload JSON" and file_input is not None:
            json_data = json.load(open(file_input.name, 'r'))
        elif input_method == "Paste JSON" and json_text:
            json_data = json.loads(json_text)
        else:
            return "❌ Please provide portfolio data", None, None, None, None, None, None, None
        
        # Validate
        is_valid, message = validate_portfolio_json(json_data)
        if not is_valid:
            return f"❌ Validation Error: {message}", None, None, None, None, None, None, None
        
        # Sanitize and process
        sanitized_data = sanitize_json_input(json_data)
        result = process_portfolio_data(sanitized_data)
        
        # Store in global state
        global portfolio_state, charts_state
        portfolio_state = result
        
        # Generate summary message
        family = result['family']
        summary = f"""
## ✅ Portfolio Analysis Complete

**Family:** {family['email']}
- **Total Value:** ₹{family['total_value']:,.2f}
- **Total Gain:** ₹{family['total_gain']:,.2f} ({family['total_gain_pct']:.2f}%)
- **Members:** {family['member_count']}
- **Unique Stocks:** {family['unique_stocks']}
- **Overlapping Stocks:** {family['overlapping_stocks']}
- **Risk Score:** {family['risk_score']}/10

**Metrics:**
- Volatility: {family['metrics']['volatility']:.4f}
- Expected Return: {family['metrics']['expected_return']:.4f}
- Sharpe Ratio: {family['metrics']['sharpe_ratio']:.4f}
- Beta: {family['metrics']['beta']:.4f}
- Diversification: {family['metrics']['diversification_score']:.2f}/10
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

        return summary, treemap, member_comparison, overlap_chart, risk_chart, gr.update(choices=member_names,
                                                                                         value=member_names[0],
                                                                                         visible=True), result
    except Exception as e:
        return f"❌ Error: {str(e)}", None, None, None, None, None, None, None

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
                'current_price': portfolio_data['members'][0]['holdings'][0]['current_price'] if portfolio_data['members'] else 0,
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
- Expected Return: {result['current']['expected_return']*100:.2f}%
- Volatility: {result['current']['volatility']*100:.2f}%
- Sharpe Ratio: {result['current']['sharpe_ratio']:.4f}

**Optimized Portfolio:**
- Expected Return: {result['optimized']['expected_return']*100:.2f}%
- Volatility: {result['optimized']['volatility']*100:.2f}%
- Sharpe Ratio: {result['optimized']['sharpe_ratio']:.4f}

**Improvements:**
- Return Change: {improvement['return_change']*100:+.2f}%
- Volatility Change: {improvement['volatility_change']*100:+.2f}%
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

**{var['confidence_level']*100:.0f}% Confidence Level:**

**Daily VaR:** {var['daily_var']*100:.2f}%  
**Annual VaR:** {var['annual_var']*100:.2f}%

**Conditional VaR (CVaR):**
- Daily: {cvar['daily_cvar']*100:.2f}%
- Annual: {cvar['annual_cvar']*100:.2f}%

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
    """Send message to AI and get response"""
    if not user_message or not user_message.strip():
        return chat_history, ""
    
    # Get chat instance with API key if provided
    api_key = api_key_input if api_key_input and api_key_input.startswith("sk-ant-") else None
    chat = get_chat_instance(api_key)
    
    # Set portfolio context
    if portfolio_data:
        chat.set_portfolio_data(portfolio_data)
    
    # Get response
    response = chat.chat(user_message)
    
    # Update chat history
    chat_history = chat_history or []
    chat_history.append((user_message, response))
    
    return chat_history, ""

def use_suggested_question(question, chat_history, portfolio_data, api_key_input):
    """Use a suggested question"""
    if question:
        return send_chat_message(question, chat_history, portfolio_data, api_key_input)
    return chat_history, ""

def clear_chat_history():
    """Clear chat history"""
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

# Create Gradio Interface
with gr.Blocks(title="Family Portfolio Analytics") as app:
    gr.Markdown("""
    # 👨‍👩‍👧‍👦 Family Portfolio Analytics
    ### Comprehensive portfolio analysis for Indian stock market investors
    """)
    
    # Store portfolio data
    portfolio_data_state = gr.State(value=None)
    
    # Input Section
    with gr.Row():
        input_method = gr.Radio(
            ["Upload JSON", "Paste JSON"],
            value="Upload JSON",
            label="Input Method"
        )
    
    with gr.Row():
        with gr.Column(scale=1):
            file_upload = gr.File(label="Upload Portfolio JSON", file_types=[".json"])
        with gr.Column(scale=1):
            json_text = gr.Textbox(
                label="Or Paste JSON Here",
                lines=10,
                placeholder='{"email": "family@example.com", "investor": [...]}'
            )
    
    analyze_btn = gr.Button("🔍 Analyze Portfolio", variant="primary", size="lg")
    
    # Results Section
    analysis_status = gr.Markdown("")
    
    # View Toggle
    with gr.Row(visible=True) as view_controls:
        view_mode = gr.Radio(
            ["Family View", "Individual View"],
            value="Family View",
            label="View Mode"
        )
        member_dropdown = gr.Dropdown(
            label="Select Member",
            visible=False
        )
    
    # Overview Tab Content
    with gr.Tabs():
        with gr.TabItem("📊 Overview"):
            with gr.Row():
                with gr.Column(scale=2):
                    treemap_chart = gr.Plot(label="Portfolio Allocation")
                with gr.Column(scale=1):
                    risk_chart = gr.Plot(label="Risk Score")
            
            with gr.Row():
                with gr.Column():
                    comparison_chart = gr.Plot(label="Member Comparison")
                with gr.Column():
                    overlap_chart = gr.Plot(label="Overlapping Holdings")
            
            with gr.Row():
                holdings_table = gr.Plot(label="Holdings Details")
        
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
            
            with gr.Row():
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
            gr.Markdown("""
            ### AI Portfolio Advisor
            Ask questions about your portfolio and get insights powered by Claude AI.
            """)
            
            with gr.Row():
                api_key_input = gr.Textbox(
                    label="Anthropic API Key (Optional)",
                    placeholder="sk-ant-...",
                    type="password",
                    scale=3
                )
                set_api_key_btn = gr.Button("Set API Key", scale=1)
            
            api_status = gr.Markdown("ℹ️ API key not set. Using environment variable if available.")
            
            with gr.Row():
                suggested_questions = gr.Dropdown(
                    label="Suggested Questions",
                    choices=[],
                    interactive=True
                )
                refresh_suggestions_btn = gr.Button("🔄 Refresh", scale=0)
            
            chatbot = gr.Chatbot(
                label="Portfolio Advisor Chat",
                height=500,
                show_label=True
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
                update_context_btn = gr.Button("🔄 Update Portfolio Context")
    
    # Export Section
    with gr.Row(visible=False) as export_section:
        export_pdf_btn = gr.Button("📥 Export Full Report to PDF", variant="primary", size="lg")
        
    pdf_output = gr.File(label="Download PDF Report", visible=False)
    export_status = gr.Markdown("")
    
    # Event Handlers
    analyze_btn.click(
        fn=process_input,
        inputs=[file_upload, json_text, input_method],
        outputs=[
            analysis_status,
            treemap_chart,
            comparison_chart,
            overlap_chart,
            risk_chart,
            view_controls,
            member_dropdown,
            portfolio_data_state
        ]
    ).then(
        fn=lambda: gr.update(visible=True),
        outputs=[export_section]
    )
    
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
    
    # Optimization tab handlers
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
            portfolio_data_state
        ]
    )
    
    # Scenarios tab handlers
    run_scenario_btn.click(
        fn=run_scenario_analysis,
        inputs=[portfolio_data_state, scenario_select],
        outputs=[scenario_results_plot, scenario_details]
    )
    
    # Risk Analysis tab handlers
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
    
    # PDF Export handler
    export_pdf_btn.click(
        fn=export_to_pdf,
        inputs=[portfolio_data_state],
        outputs=[pdf_output, export_status]
    ).then(
        fn=lambda x: gr.update(visible=True) if x else gr.update(visible=False),
        inputs=[pdf_output],
        outputs=[pdf_output]
    )
    
    # AI Chat tab handlers
    set_api_key_btn.click(
        fn=set_api_key,
        inputs=[api_key_input],
        outputs=[api_status]
    )
    
    refresh_suggestions_btn.click(
        fn=refresh_suggested_questions_fn,
        inputs=[portfolio_data_state],
        outputs=[suggested_questions]
    )
    
    # Auto-refresh suggestions when portfolio is loaded
    analyze_btn.click(
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
