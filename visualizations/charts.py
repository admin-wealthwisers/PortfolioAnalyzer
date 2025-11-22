import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

def create_family_treemap(portfolio_data):
    """Create treemap showing family portfolio allocation"""
    family_holdings = portfolio_data['family_holdings']
    
    labels = []
    parents = []
    values = []
    colors = []
    
    # Root
    labels.append("Family Portfolio")
    parents.append("")
    values.append(portfolio_data['family']['total_value'])
    colors.append(0)
    
    # Add each stock
    for symbol, data in family_holdings.items():
        labels.append(f"{symbol}<br>₹{data['value']:,.0f}")
        parents.append("Family Portfolio")
        values.append(data['value'])
        colors.append(data['weight'])
    
    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(
            colorscale='Viridis',
            cmid=50,
            colorbar=dict(title="Weight %")
        ),
        textposition="middle center",
        textfont=dict(size=14)
    ))
    
    fig.update_layout(
        title="Family Portfolio Allocation",
        height=500,
        margin=dict(t=50, l=0, r=0, b=0)
    )
    
    return fig

def create_member_treemap(member_data):
    """Create treemap for individual member"""
    labels = [f"{member_data['name']}'s Portfolio"]
    parents = [""]
    values = [member_data['value']]
    colors = [0]
    
    for holding in member_data['holdings']:
        labels.append(f"{holding['symbol']}<br>₹{holding['value']:,.0f}")
        parents.append(f"{member_data['name']}'s Portfolio")
        values.append(holding['value'])
        colors.append(holding['weight'])
    
    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(
            colorscale='Blues',
            colorbar=dict(title="Weight %")
        ),
        textposition="middle center"
    ))
    
    fig.update_layout(
        title=f"{member_data['name']}'s Portfolio Allocation",
        height=400,
        margin=dict(t=50, l=0, r=0, b=0)
    )
    
    return fig

def create_allocation_pie(holdings_data, title="Portfolio Allocation"):
    """Create pie chart for allocation"""
    symbols = [h['symbol'] for h in holdings_data]
    values = [h['value'] for h in holdings_data]
    
    fig = go.Figure(data=[go.Pie(
        labels=symbols,
        values=values,
        hole=0.4,
        textposition='auto',
        textinfo='label+percent'
    )])
    
    fig.update_layout(
        title=title,
        height=400,
        showlegend=True
    )
    
    return fig

def create_member_comparison_bar(members_data):
    """Create bar chart comparing members"""
    names = [m['name'] for m in members_data]
    values = [m['value'] for m in members_data]
    gains = [m['gain_pct'] for m in members_data]
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Portfolio Value", "Gain %"),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Portfolio values
    fig.add_trace(
        go.Bar(
            x=names,
            y=values,
            name="Value (₹)",
            marker_color='lightblue',
            text=[f"₹{v:,.0f}" for v in values],
            textposition='auto'
        ),
        row=1, col=1
    )
    
    # Gains
    colors = ['green' if g > 0 else 'red' for g in gains]
    fig.add_trace(
        go.Bar(
            x=names,
            y=gains,
            name="Gain %",
            marker_color=colors,
            text=[f"{g:.1f}%" for g in gains],
            textposition='auto'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title="Member Portfolio Comparison",
        height=400,
        showlegend=False
    )
    
    return fig

def create_holdings_table(holdings_data):
    """Create table showing holdings details"""
    df = pd.DataFrame(holdings_data)
    
    # Select and format columns
    table_data = df[['symbol', 'quantity', 'current_price', 'value', 'weight', 'gain_pct']].copy()
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['Symbol', 'Quantity', 'Current Price', 'Value', 'Weight %', 'Gain %'],
            fill_color='paleturquoise',
            align='left',
            font=dict(size=12, color='black')
        ),
        cells=dict(
            values=[
                table_data['symbol'],
                table_data['quantity'],
                [f"₹{p:.2f}" for p in table_data['current_price']],
                [f"₹{v:,.2f}" for v in table_data['value']],
                [f"{w:.1f}%" for w in table_data['weight']],
                [f"{g:.1f}%" for g in table_data['gain_pct']]
            ],
            fill_color='lavender',
            align='left',
            font=dict(size=11)
        )
    )])
    
    fig.update_layout(
        title="Holdings Details",
        height=min(400, len(holdings_data) * 40 + 100),
        margin=dict(t=50, l=0, r=0, b=0)
    )
    
    return fig

def create_metrics_gauge(value, title, max_value=10, color='blue'):
    """Create gauge chart for a metric"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title},
        gauge={
            'axis': {'range': [0, max_value]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, max_value/3], 'color': "lightgray"},
                {'range': [max_value/3, 2*max_value/3], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.8
            }
        }
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(t=50, l=20, r=20, b=20)
    )
    
    return fig

def create_overlap_chart(overlaps_data):
    """Create chart showing overlapping holdings"""
    if not overlaps_data:
        fig = go.Figure()
        fig.add_annotation(
            text="No overlapping holdings detected",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=300)
        return fig
    
    symbols = list(overlaps_data.keys())
    owners = [len(overlaps_data[s]) for s in symbols]
    
    fig = go.Figure(data=[
        go.Bar(
            x=symbols,
            y=owners,
            text=[f"{o} members" for o in owners],
            textposition='auto',
            marker_color='coral'
        )
    ])
    
    fig.update_layout(
        title="Overlapping Holdings (Risk Alert)",
        xaxis_title="Stock Symbol",
        yaxis_title="Number of Members",
        height=300
    )
    
    return fig

def create_risk_indicator(risk_score):
    """Create visual risk indicator"""
    if risk_score < 3:
        color = 'green'
        level = 'Low Risk'
    elif risk_score < 6:
        color = 'orange'
        level = 'Moderate Risk'
    else:
        color = 'red'
        level = 'High Risk'
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=risk_score,
        title={'text': f"Risk Score<br><span style='font-size:0.8em'>{level}</span>"},
        gauge={
            'axis': {'range': [0, 10]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 3], 'color': "lightgreen"},
                {'range': [3, 6], 'color': "lightyellow"},
                {'range': [6, 10], 'color': "lightcoral"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 7
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(t=50, l=20, r=20, b=20)
    )
    
    return fig

def create_efficient_frontier(frontier_data, current_point=None, optimal_point=None):
    """Create efficient frontier visualization"""
    fig = go.Figure()
    
    # Efficient frontier curve
    fig.add_trace(go.Scatter(
        x=frontier_data['volatility'],
        y=[r * 100 for r in frontier_data['returns']],  # Convert to percentage
        mode='lines',
        name='Efficient Frontier',
        line=dict(color='blue', width=2),
        hovertemplate='Volatility: %{x:.2%}<br>Return: %{y:.2f}%<extra></extra>'
    ))
    
    # Current portfolio
    if current_point:
        fig.add_trace(go.Scatter(
            x=[current_point['volatility']],
            y=[current_point['expected_return'] * 100],
            mode='markers',
            name='Current Portfolio',
            marker=dict(size=15, color='red', symbol='circle'),
            hovertemplate='Current<br>Volatility: %{x:.2%}<br>Return: %{y:.2f}%<extra></extra>'
        ))
    
    # Optimal portfolio
    if optimal_point:
        fig.add_trace(go.Scatter(
            x=[optimal_point['volatility']],
            y=[optimal_point['expected_return'] * 100],
            mode='markers',
            name='Optimized Portfolio',
            marker=dict(size=15, color='green', symbol='star'),
            hovertemplate='Optimized<br>Volatility: %{x:.2%}<br>Return: %{y:.2f}%<extra></extra>'
        ))
    
    fig.update_layout(
        title='Efficient Frontier',
        xaxis_title='Volatility (Risk)',
        yaxis_title='Expected Return (%)',
        height=500,
        hovermode='closest',
        showlegend=True
    )
    
    fig.update_xaxes(tickformat='.1%')
    
    return fig

def create_weights_comparison(current_weights, optimized_weights, title="Current vs Optimized Allocation"):
    """Create side-by-side comparison of current and optimized weights"""
    symbols = sorted(set(list(current_weights.keys()) + list(optimized_weights.keys())))
    
    current = [current_weights.get(s, 0) * 100 for s in symbols]
    optimized = [optimized_weights.get(s, 0) * 100 for s in symbols]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Current',
        x=symbols,
        y=current,
        marker_color='lightblue'
    ))
    
    fig.add_trace(go.Bar(
        name='Optimized',
        x=symbols,
        y=optimized,
        marker_color='lightgreen'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Stock',
        yaxis_title='Weight (%)',
        barmode='group',
        height=400
    )
    
    return fig

def create_rebalancing_table(trades):
    """Create table showing rebalancing recommendations"""
    if not trades:
        fig = go.Figure()
        fig.add_annotation(
            text="No rebalancing needed",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=300)
        return fig
    
    df = pd.DataFrame(trades)
    
    # Color code actions
    action_colors = ['lightgreen' if a == 'BUY' else 'lightcoral' for a in df['action']]
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['Symbol', 'Action', 'Quantity', 'Value', 'Current %', 'Target %', 'Change'],
            fill_color='paleturquoise',
            align='left',
            font=dict(size=12, color='black')
        ),
        cells=dict(
            values=[
                df['symbol'],
                df['action'],
                [f"{q:.2f}" for q in df['quantity']],
                [f"₹{v:,.0f}" for v in df['value']],
                [f"{w:.1f}%" for w in df['current_weight']],
                [f"{w:.1f}%" for w in df['target_weight']],
                [f"{w:+.1f}%" for w in df['weight_change']]
            ],
            fill_color=[['white'] * len(df), action_colors] + [['white'] * len(df)] * 5,
            align='left',
            font=dict(size=11)
        )
    )])
    
    fig.update_layout(
        title="Rebalancing Recommendations",
        height=min(400, len(trades) * 40 + 100),
        margin=dict(t=50, l=0, r=0, b=0)
    )
    
    return fig

def create_correlation_heatmap(corr_matrix):
    """Create correlation heatmap"""
    if corr_matrix.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Insufficient data for correlation analysis",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=400)
        return fig
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale='RdBu',
        zmid=0,
        text=corr_matrix.values,
        texttemplate='%{text:.2f}',
        textfont={"size": 10},
        colorbar=dict(title="Correlation")
    ))
    
    fig.update_layout(
        title='Stock Correlation Matrix',
        height=500,
        xaxis={'side': 'bottom'},
        yaxis={'side': 'left'}
    )
    
    return fig

def create_risk_contribution_chart(risk_contributions):
    """Create chart showing risk contribution by holding"""
    if not risk_contributions:
        fig = go.Figure()
        fig.add_annotation(
            text="No risk contribution data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=300)
        return fig
    
    df = pd.DataFrame(risk_contributions)
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Portfolio Weight", "Risk Contribution"),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    fig.add_trace(
        go.Bar(
            x=df['symbol'],
            y=df['weight'],
            name="Weight %",
            marker_color='lightblue',
            text=[f"{w:.1f}%" for w in df['weight']],
            textposition='auto'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df['symbol'],
            y=df['risk_contribution'],
            name="Risk %",
            marker_color='lightcoral',
            text=[f"{r:.1f}%" for r in df['risk_contribution']],
            textposition='auto'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title="Risk Contribution Analysis",
        height=400,
        showlegend=False
    )
    
    return fig

def create_scenario_comparison(scenario_results):
    """Create chart comparing different scenarios"""
    if not scenario_results:
        fig = go.Figure()
        fig.add_annotation(
            text="No scenario data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=300)
        return fig
    
    df = pd.DataFrame(scenario_results)
    
    # Color code based on gain/loss
    colors = ['green' if pct > 0 else 'red' for pct in df['pct_change']]
    
    fig = go.Figure(data=[
        go.Bar(
            x=df['scenario'],
            y=df['pct_change'],
            marker_color=colors,
            text=[f"{pct:+.2f}%" for pct in df['pct_change']],
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title="Scenario Analysis",
        xaxis_title="Scenario",
        yaxis_title="Portfolio Change (%)",
        height=400
    )
    
    return fig
