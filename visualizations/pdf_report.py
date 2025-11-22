"""
PDF Report Generator for Portfolio Analytics
Creates professional PDF reports with charts and metrics
"""

import io
import base64
from datetime import datetime

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    print("Warning: WeasyPrint not available. PDF export disabled.")

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

def fig_to_base64(fig):
    """Convert Plotly figure to base64 encoded PNG"""
    if not PLOTLY_AVAILABLE:
        return ""
    
    try:
        # Convert to PNG bytes
        img_bytes = fig.to_image(format="png", width=800, height=500)
        
        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        print(f"Error converting figure to image: {e}")
        return ""

def generate_html_report(portfolio_data, charts_dict=None, optimization_result=None, risk_data=None):
    """
    Generate HTML report from portfolio data
    
    Args:
        portfolio_data: Processed portfolio data
        charts_dict: Dictionary of Plotly figures
        optimization_result: Optimization results
        risk_data: Risk analysis data
    
    Returns:
        HTML string
    """
    
    if not portfolio_data:
        return "<html><body><h1>No portfolio data available</h1></body></html>"
    
    family = portfolio_data['family']
    members = portfolio_data['members']
    overlaps = portfolio_data.get('overlaps', {})
    
    # Convert charts to base64 if provided
    chart_images = {}
    if charts_dict and PLOTLY_AVAILABLE:
        for chart_name, fig in charts_dict.items():
            if fig:
                chart_images[chart_name] = fig_to_base64(fig)
    
    # Get current date
    report_date = datetime.now().strftime("%B %d, %Y")
    
    # Build HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Portfolio Analysis Report - {family['email']}</title>
    <style>
        @page {{
            size: A4;
            margin: 1.5cm;
        }}
        
        body {{
            font-family: 'Helvetica', 'Arial', sans-serif;
            line-height: 1.6;
            color: #333;
            font-size: 11pt;
        }}
        
        .header {{
            text-align: center;
            border-bottom: 3px solid #2c3e50;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            color: #2c3e50;
            font-size: 28pt;
            margin: 10px 0;
        }}
        
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 14pt;
        }}
        
        .section {{
            margin: 30px 0;
            page-break-inside: avoid;
        }}
        
        .section h2 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            font-size: 18pt;
            margin-top: 20px;
        }}
        
        .section h3 {{
            color: #34495e;
            font-size: 14pt;
            margin-top: 15px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin: 20px 0;
        }}
        
        .metric-card {{
            background: #ecf0f1;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }}
        
        .metric-label {{
            color: #7f8c8d;
            font-size: 10pt;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        
        .metric-value {{
            font-size: 20pt;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .metric-subvalue {{
            color: #7f8c8d;
            font-size: 11pt;
        }}
        
        .positive {{
            color: #27ae60;
        }}
        
        .negative {{
            color: #e74c3c;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 10pt;
        }}
        
        th {{
            background-color: #34495e;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}
        
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }}
        
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        .alert {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        
        .alert-danger {{
            background-color: #f8d7da;
            border-left-color: #dc3545;
        }}
        
        .alert-success {{
            background-color: #d4edda;
            border-left-color: #28a745;
        }}
        
        .chart-container {{
            text-align: center;
            margin: 20px 0;
            page-break-inside: avoid;
        }}
        
        .chart-container img {{
            max-width: 100%;
            height: auto;
        }}
        
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ddd;
            text-align: center;
            color: #7f8c8d;
            font-size: 9pt;
        }}
        
        .page-break {{
            page-break-after: always;
        }}
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>👨‍👩‍👧‍👦 Family Portfolio Analysis Report</h1>
        <div class="subtitle">{family['email']}</div>
        <div class="subtitle">Generated on {report_date}</div>
    </div>
    
    <!-- Executive Summary -->
    <div class="section">
        <h2>📊 Executive Summary</h2>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total Portfolio Value</div>
                <div class="metric-value">₹{family['total_value']:,.2f}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Total Gain/Loss</div>
                <div class="metric-value {'positive' if family['total_gain'] > 0 else 'negative'}">
                    ₹{family['total_gain']:,.2f}
                </div>
                <div class="metric-subvalue">({family['total_gain_pct']:+.2f}%)</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Family Members</div>
                <div class="metric-value">{family['member_count']}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Unique Stocks</div>
                <div class="metric-value">{family['unique_stocks']}</div>
                <div class="metric-subvalue">{family['overlapping_stocks']} overlapping</div>
            </div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Risk Score</div>
                <div class="metric-value">{family['risk_score']:.2f}/10</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Sharpe Ratio</div>
                <div class="metric-value">{family['metrics']['sharpe_ratio']:.4f}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Portfolio Volatility</div>
                <div class="metric-value">{family['metrics']['volatility']*100:.2f}%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Diversification Score</div>
                <div class="metric-value">{family['metrics']['diversification_score']:.2f}/10</div>
            </div>
        </div>
    </div>
    
    <!-- Alerts -->
    {generate_alerts_section(family, overlaps)}
    
    <!-- Portfolio Allocation Chart -->
    {generate_chart_section('Portfolio Allocation', chart_images.get('treemap', ''))}
    
    <div class="page-break"></div>
    
    <!-- Member Analysis -->
    <div class="section">
        <h2>👥 Member Portfolio Analysis</h2>
        
        {generate_members_table(members)}
        
        {generate_chart_section('Member Comparison', chart_images.get('member_comparison', ''))}
    </div>
    
    <!-- Holdings Details -->
    <div class="section">
        <h2>📈 Portfolio Holdings</h2>
        {generate_holdings_table(portfolio_data['family_holdings'])}
    </div>
    
    {generate_individual_members_section(members)}
    
    <div class="page-break"></div>
    
    <!-- Optimization Results -->
    {generate_optimization_section(optimization_result, chart_images) if optimization_result else ''}
    
    <!-- Risk Analysis -->
    {generate_risk_section(risk_data, chart_images) if risk_data else ''}
    
    <!-- Footer -->
    <div class="footer">
        <p>This report was generated by Family Portfolio Analytics Platform</p>
        <p>Data is for informational purposes only and should not be considered as investment advice.</p>
        <p>Please consult with a qualified financial advisor before making investment decisions.</p>
    </div>
</body>
</html>
"""
    
    return html

def generate_alerts_section(family, overlaps):
    """Generate alerts section"""
    alerts = []
    
    # Risk alert
    if family['risk_score'] > 6:
        alerts.append('<div class="alert alert-danger"><strong>⚠️ High Risk Alert:</strong> Your portfolio risk score is high. Consider diversifying your holdings.</div>')
    
    # Overlap alert
    if overlaps:
        overlap_text = ', '.join(overlaps.keys())
        alerts.append(f'<div class="alert alert-danger"><strong>🔴 Overlapping Holdings:</strong> Multiple family members own: {overlap_text}. This increases concentration risk.</div>')
    
    # Diversification alert
    if family['metrics']['diversification_score'] < 5:
        alerts.append('<div class="alert alert-danger"><strong>📉 Low Diversification:</strong> Your portfolio could benefit from more diversification across different sectors and stocks.</div>')
    
    # Performance alert
    if family['total_gain_pct'] > 20:
        alerts.append('<div class="alert alert-success"><strong>🎉 Strong Performance:</strong> Your portfolio has shown excellent returns. Consider rebalancing to lock in gains.</div>')
    
    if not alerts:
        alerts.append('<div class="alert alert-success"><strong>✅ Portfolio Health:</strong> No major concerns detected. Continue monitoring your portfolio regularly.</div>')
    
    return '\n'.join(alerts)

def generate_chart_section(title, chart_base64):
    """Generate chart section"""
    if not chart_base64:
        return ''
    
    return f"""
    <div class="section chart-container">
        <h3>{title}</h3>
        <img src="{chart_base64}" alt="{title}">
    </div>
    """

def generate_members_table(members):
    """Generate members summary table"""
    rows = []
    for member in members:
        gain_class = 'positive' if member['gain_pct'] > 0 else 'negative'
        rows.append(f"""
        <tr>
            <td><strong>{member['name']}</strong></td>
            <td>₹{member['value']:,.2f}</td>
            <td class="{gain_class}">{member['gain_pct']:+.2f}%</td>
            <td>{member['holdings_count']}</td>
            <td>{member['metrics']['sharpe_ratio']:.4f}</td>
            <td>{member['metrics']['diversification_score']:.2f}/10</td>
        </tr>
        """)
    
    return f"""
    <table>
        <thead>
            <tr>
                <th>Member</th>
                <th>Portfolio Value</th>
                <th>Gain %</th>
                <th>Holdings</th>
                <th>Sharpe Ratio</th>
                <th>Diversification</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
    """

def generate_holdings_table(family_holdings):
    """Generate family holdings table"""
    sorted_holdings = sorted(family_holdings.items(), key=lambda x: x[1]['value'], reverse=True)
    
    rows = []
    for symbol, data in sorted_holdings:
        rows.append(f"""
        <tr>
            <td><strong>{symbol}</strong></td>
            <td>{data['quantity']:.2f}</td>
            <td>₹{data['value']:,.2f}</td>
            <td>{data['weight']:.2f}%</td>
            <td>{', '.join(data['owners'])}</td>
        </tr>
        """)
    
    return f"""
    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Total Quantity</th>
                <th>Total Value</th>
                <th>Weight %</th>
                <th>Owned By</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
    """

def generate_individual_members_section(members):
    """Generate detailed section for each member"""
    sections = []
    
    for member in members:
        holdings_rows = []
        for holding in sorted(member['holdings'], key=lambda x: x['value'], reverse=True):
            gain_class = 'positive' if holding['gain_pct'] > 0 else 'negative'
            holdings_rows.append(f"""
            <tr>
                <td><strong>{holding['symbol']}</strong></td>
                <td>{holding['quantity']}</td>
                <td>₹{holding['current_price']:.2f}</td>
                <td>₹{holding['value']:,.2f}</td>
                <td>{holding['weight']:.2f}%</td>
                <td class="{gain_class}">{holding['gain_pct']:+.2f}%</td>
            </tr>
            """)
        
        sections.append(f"""
        <div class="section">
            <h3>📊 {member['name']}'s Portfolio</h3>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Portfolio Value</div>
                    <div class="metric-value">₹{member['value']:,.2f}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Total Gain</div>
                    <div class="metric-value {'positive' if member['gain_pct'] > 0 else 'negative'}">
                        {member['gain_pct']:+.2f}%
                    </div>
                </div>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Value</th>
                        <th>Weight %</th>
                        <th>Gain %</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(holdings_rows)}
                </tbody>
            </table>
        </div>
        """)
    
    return '\n'.join(sections)

def generate_optimization_section(optimization_result, chart_images):
    """Generate optimization section"""
    if not optimization_result:
        return ''
    
    current = optimization_result['current']
    optimized = optimization_result['optimized']
    improvement = optimization_result['improvement']
    
    trades_rows = []
    for trade in optimization_result.get('trades', [])[:10]:
        action_class = 'positive' if trade['action'] == 'BUY' else 'negative'
        trades_rows.append(f"""
        <tr>
            <td><strong>{trade['symbol']}</strong></td>
            <td class="{action_class}">{trade['action']}</td>
            <td>{trade['quantity']:.2f}</td>
            <td>₹{trade['value']:,.0f}</td>
            <td>{trade['current_weight']:.2f}%</td>
            <td>{trade['target_weight']:.2f}%</td>
            <td>{trade['weight_change']:+.2f}%</td>
        </tr>
        """)
    
    return f"""
    <div class="page-break"></div>
    
    <div class="section">
        <h2>⚡ Portfolio Optimization</h2>
        
        <h3>Current vs Optimized Portfolio</h3>
        
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Current</th>
                    <th>Optimized</th>
                    <th>Improvement</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Expected Return</strong></td>
                    <td>{current['expected_return']*100:.2f}%</td>
                    <td>{optimized['expected_return']*100:.2f}%</td>
                    <td class="{'positive' if improvement['return_change'] > 0 else 'negative'}">{improvement['return_change']*100:+.2f}%</td>
                </tr>
                <tr>
                    <td><strong>Volatility</strong></td>
                    <td>{current['volatility']*100:.2f}%</td>
                    <td>{optimized['volatility']*100:.2f}%</td>
                    <td class="{'negative' if improvement['volatility_change'] > 0 else 'positive'}">{improvement['volatility_change']*100:+.2f}%</td>
                </tr>
                <tr>
                    <td><strong>Sharpe Ratio</strong></td>
                    <td>{current['sharpe_ratio']:.4f}</td>
                    <td>{optimized['sharpe_ratio']:.4f}</td>
                    <td class="{'positive' if improvement['sharpe_change'] > 0 else 'negative'}">{improvement['sharpe_change']:+.4f}</td>
                </tr>
            </tbody>
        </table>
        
        {generate_chart_section('Efficient Frontier', chart_images.get('efficient_frontier', ''))}
        
        <h3>Recommended Rebalancing Actions</h3>
        
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Action</th>
                    <th>Quantity</th>
                    <th>Value</th>
                    <th>Current Weight</th>
                    <th>Target Weight</th>
                    <th>Change</th>
                </tr>
            </thead>
            <tbody>
                {''.join(trades_rows) if trades_rows else '<tr><td colspan="7">No rebalancing needed</td></tr>'}
            </tbody>
        </table>
    </div>
    """

def generate_risk_section(risk_data, chart_images):
    """Generate risk analysis section"""
    if not risk_data:
        return ''
    
    conc = risk_data['concentration_risk']
    var_html = ''
    
    if risk_data['var']:
        var = risk_data['var']
        cvar = risk_data['cvar']
        var_html = f"""
        <h3>Value at Risk (VaR)</h3>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Daily VaR ({var['confidence_level']*100:.0f}%)</div>
                <div class="metric-value negative">{var['daily_var']*100:.2f}%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Annual VaR</div>
                <div class="metric-value negative">{var['annual_var']*100:.2f}%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Daily CVaR</div>
                <div class="metric-value negative">{cvar['daily_cvar']*100:.2f}%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Annual CVaR</div>
                <div class="metric-value negative">{cvar['annual_cvar']*100:.2f}%</div>
            </div>
        </div>
        """
    
    return f"""
    <div class="page-break"></div>
    
    <div class="section">
        <h2>⚠️ Risk Analysis</h2>
        
        <h3>Concentration Risk</h3>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">HHI Index</div>
                <div class="metric-value">{conc['hhi']:.2f}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Top Stock Concentration</div>
                <div class="metric-value">{conc['top_1_concentration']:.2f}%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Top 3 Stocks</div>
                <div class="metric-value">{conc['top_3_concentration']:.2f}%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Risk Level</div>
                <div class="metric-value" style="font-size: 14pt;">{conc['concentration_level']}</div>
                <div class="metric-subvalue">{conc['risk_rating']}</div>
            </div>
        </div>
        
        {var_html}
        
        {generate_chart_section('Correlation Heatmap', chart_images.get('correlation', ''))}
        
        {generate_chart_section('Risk Contribution', chart_images.get('risk_contribution', ''))}
    </div>
    """

def generate_pdf_report(portfolio_data, charts_dict=None, optimization_result=None, risk_data=None, output_path='portfolio_report.pdf'):
    """
    Generate PDF report
    
    Args:
        portfolio_data: Processed portfolio data
        charts_dict: Dictionary of Plotly figures
        optimization_result: Optimization results
        risk_data: Risk analysis data
        output_path: Output PDF file path
    
    Returns:
        Path to generated PDF file or None if failed
    """
    
    if not WEASYPRINT_AVAILABLE:
        print("Error: WeasyPrint not available. Cannot generate PDF.")
        return None
    
    try:
        # Generate HTML
        html_content = generate_html_report(
            portfolio_data,
            charts_dict,
            optimization_result,
            risk_data
        )
        
        # Convert to PDF
        HTML(string=html_content).write_pdf(output_path)
        
        return output_path
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return None
