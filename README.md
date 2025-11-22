# 👨‍👩‍👧‍👦 Family Portfolio Analytics Platform

> **Comprehensive portfolio analysis, optimization, and AI-powered insights for Indian stock market investors**

Built for the **MCP 1st Birthday Hackathon** | Powered by **Claude AI, Gradio, and Python**

---

## 🌟 Features

### 📊 Portfolio Analysis
- **Family-level aggregation** - Analyze multiple investors together
- **Individual member breakdown** - Detailed metrics for each family member
- **Real-time stock data** - PostgreSQL + yfinance integration
- **Overlap detection** - Identify duplicate holdings across family
- **Risk scoring** - Comprehensive 0-10 risk assessment

### ⚡ Portfolio Optimization
- **3 Optimization methods**: Max Sharpe Ratio, Min Volatility, Equal Weight
- **Efficient frontier** - Visualize risk-return tradeoffs
- **Rebalancing recommendations** - Specific buy/sell actions
- **Performance improvements** - Expected return, volatility, Sharpe ratio changes

### 🔮 Scenario Analysis
- **4 Predefined scenarios**: Market Crash, Rally, Tech Selloff, Banking Rally
- **Custom scenarios** - Test specific stock movements
- **Visual impact** - See portfolio changes instantly
- **What-if analysis** - Plan for different market conditions

### ⚠️ Risk Analysis
- **Correlation matrix** - Understand stock relationships
- **Value at Risk (VaR)** - 95% confidence loss estimation
- **Concentration risk** - HHI index and top holdings analysis
- **Risk contribution** - See which stocks add the most risk

### 💬 AI Portfolio Advisor
- **Claude-powered chat** - Ask questions about your portfolio
- **Smart suggestions** - Context-aware question recommendations
- **Natural language** - No finance jargon required
- **Actionable insights** - Practical advice based on your data

### 📥 PDF Export
- **Professional reports** - Print-ready, shareable documents
- **All visualizations** - Charts embedded as images
- **Comprehensive sections** - Overview, optimization, risk analysis
- **Financial advisor ready** - Professional formatting and disclaimers

---

## 🚀 Quick Start

### Installation

```bash
# Clone or download the project
cd portfolio-analytics

# Install dependencies
pip install -r requirements.txt

# Set API key for AI chat (optional)
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# Run the application
python app.py
```

Access at: **http://localhost:7860**

### Sample Usage

1. **Upload** `sample_portfolio.json` or paste JSON
2. Click **"Analyze Portfolio"**
3. Explore tabs: Overview, Optimization, Scenarios, Risk, AI Chat
4. Click **"Export Full Report to PDF"** to download

---

## 📋 Input Format

### JSON Structure

```json
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
```

### Validation Rules
- **Email**: Valid format, unique family ID
- **Investor ID**: Alphanumeric, unique within family
- **Symbol**: Must exist in NSE Nifty 500
- **Quantity**: Positive number
- **Cost Basis**: Optional, average purchase price
- **Limits**: 1-20 members, 1-50 stocks per member

---

## 🎨 User Interface

### 5 Interactive Tabs

1. **📊 Overview** - Portfolio metrics, allocation treemap, member comparison
2. **⚡ Optimization** - Efficient frontier, rebalancing recommendations
3. **🔮 Scenarios** - What-if analysis with 4 market scenarios
4. **⚠️ Risk Analysis** - Correlation heatmap, VaR, concentration metrics
5. **💬 Ask AI** - Claude-powered portfolio advisor chat

### View Modes
- **Family View** - Aggregated portfolio across all members
- **Individual View** - Select specific member for detailed analysis

---

## 🏗️ Architecture

### Tech Stack

```
Frontend:  Gradio 6.x (MCP support)
Backend:   Python 3.10+
Database:  PostgreSQL (Neon)
Data:      yfinance (real-time prices)
Compute:   scipy, PyPortfolioOpt
Viz:       Plotly (13 chart types)
LLM:       Anthropic Claude API
PDF:       WeasyPrint + Kaleido
```

### Project Structure

```
portfolio-analytics/
├── app.py                    # Main Gradio application
├── requirements.txt
├── database/
│   ├── db_connection.py      # PostgreSQL connector
│   ├── queries.py            # SQL queries
│   ├── data_loader.py        # Data fetching
│   └── mock_data.py          # Offline testing
├── portfolio/
│   ├── aggregator.py         # Family/member aggregation
│   ├── calculator.py         # Metrics (Sharpe, beta, volatility)
│   ├── optimizer.py          # Portfolio optimization
│   └── risk_analyzer.py      # Risk calculations
├── visualizations/
│   ├── charts.py             # 13 Plotly charts
│   └── pdf_report.py         # PDF generation
├── llm/
│   ├── context_builder.py    # LLM context formatting
│   └── chat.py               # Claude API integration
├── utils/
│   └── validators.py         # Input validation
└── sample_*.json             # Test portfolios
```

---

## 📊 Key Calculations

### Risk Metrics

```python
# Sharpe Ratio
sharpe = (expected_return - risk_free_rate) / volatility

# Beta (vs Nifty 50)
beta = covariance(stock, market) / variance(market)

# VaR (95% confidence)
var = percentile(daily_returns, 5)
```

### Optimization

```python
# Max Sharpe Ratio
maximize: (portfolio_return - risk_free_rate) / portfolio_volatility
subject to: sum(weights) = 1, weights >= 0

# Min Volatility
minimize: sqrt(weights.T * cov_matrix * weights)
subject to: sum(weights) = 1, weights >= 0
```

### Risk Scoring (0-10)

- Volatility component: 0-3 points
- Beta deviation: 0-2 points  
- Diversification: 0-3 points (inverted)
- Overlap penalty: 0-2 points

---

## 🎯 Use Cases

### For Families
- **Aggregate view** - See total family wealth
- **Detect duplicates** - Find overlapping holdings
- **Optimize together** - Family-wide rebalancing
- **Risk management** - Understand combined risk

### For Individual Investors
- **Portfolio analysis** - Comprehensive metrics
- **Rebalancing guide** - Specific buy/sell recommendations
- **Risk assessment** - VaR, correlation, concentration
- **AI advice** - Ask questions about your portfolio

### For Financial Advisors
- **Client reports** - Professional PDF exports
- **Optimization tool** - Show efficient frontier
- **Risk communication** - Visual heatmaps and charts
- **Scenario planning** - Demonstrate market impact

---

## 🔐 Configuration

### Environment Variables

```bash
# Database (required for real data)
DB_HOST=your-postgres-host
DB_NAME=market_data
DB_USER=your-username
DB_PASSWORD=your-password

# AI Chat (optional)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# App Config
RISK_FREE_RATE=0.065
DEFAULT_LOOKBACK_DAYS=252
```

### API Key Setup

**Option 1: Environment Variable** (recommended)
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**Option 2: UI Input**
- Go to "Ask AI" tab
- Enter key in password field
- Click "Set API Key"

Get your key: https://console.anthropic.com/

---

## 📈 Sample Results

### Singh Family Portfolio

```
Total Value:      ₹7,45,301.50
Total Gain:       ₹1,03,001.50 (16.04%)
Members:          3
Stocks:           7 unique
Overlaps:         2 (RELIANCE, TCS)
Risk Score:       2.58/10 (Low)
Sharpe Ratio:     -0.69
Diversification:  5.5/10

Optimization Improvement:
- Sharpe Ratio:   -0.69 → 0.47 (+1.15)
- Expected Return: 13.92% → 16.24%
- Volatility:     17.07% → 16.43%
- Trades Needed:  7 rebalancing actions
```

---

## 🧪 Testing

### Run Tests

```bash
# Phase 1: Core data pipeline
python test_phase1.py

# Phase 2: Visualizations  
python test_phase2.py

# Phase 3: Optimization & risk
python test_phase3.py

# Phase 4: AI chat
python test_phase4.py

# Phase 5: PDF export
python test_phase5.py
```

### Sample Data

- `sample_simple.json` - 1 member, 2 stocks (testing)
- `sample_portfolio.json` - 3 members, 7 stocks (Singh family)
- `sample_overlap.json` - High overlap scenario (Patel family)
- `sample_diversified.json` - Well-diversified (Kumar family)

---

## 🚢 Deployment

### Hugging Face Spaces

1. Create new Space (Gradio SDK)
2. Upload all project files
3. Add secrets in Settings:
   - `ANTHROPIC_API_KEY`
   - Database credentials
4. Space auto-deploys!

### Local Production

```bash
# Install production dependencies
pip install -r requirements.txt --break-system-packages

# Set environment variables
export ANTHROPIC_API_KEY=sk-ant-...

# Run with gunicorn (optional)
gunicorn app:app -b 0.0.0.0:7860
```

---

## 📚 Documentation

### Phase Documentation
- [Phase 1: Core Data Pipeline](PHASE1_COMPLETE.md) (if exists)
- [Phase 2: UI + Overview](PHASE2_COMPLETE.md) (if exists)
- [Phase 3: Optimization & Risk](PHASE3_COMPLETE.md)
- [Phase 4: AI Chat Integration](PHASE4_COMPLETE.md)
- [Phase 5: PDF Export](PHASE5_COMPLETE.md)

### Key Concepts

**Sharpe Ratio**: Risk-adjusted return (higher is better)  
**Beta**: Sensitivity to market movements (1.0 = market average)  
**VaR**: Maximum expected loss at confidence level  
**HHI**: Concentration index (higher = more concentrated)  
**Efficient Frontier**: Optimal risk-return combinations

---

## 🤝 Contributing

This project was built for the MCP 1st Birthday Hackathon. Feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Use for your own portfolios

---

## ⚠️ Disclaimer

This tool is for **informational and educational purposes only**. It is **not investment advice**.

- Past performance does not guarantee future results
- Always consult a qualified financial advisor
- Invest only what you can afford to lose
- Do your own research before investing

---

## 📝 License

MIT License - Free to use and modify

---

## 🙏 Acknowledgments

- **Anthropic** - Claude AI API
- **Gradio** - Amazing UI framework with MCP support
- **Plotly** - Beautiful interactive visualizations
- **PyPortfolioOpt** - Portfolio optimization algorithms
- **yfinance** - Stock market data
- **Neon** - PostgreSQL database hosting

---

## 📧 Contact

For questions or support:
- GitHub Issues (if repository)
- Hackathon Discord
- Email (if provided)

---

## 🎯 Project Stats

**Lines of Code**: ~7,500  
**Python Files**: 20  
**Functions**: ~80  
**Charts**: 13 types  
**Features**: 6 major  
**Test Files**: 5  
**Documentation**: Comprehensive

**Status**: ✅ **PRODUCTION READY**

---

**Built with ❤️ for MCP 1st Birthday Hackathon**

*Making family portfolio management accessible, intelligent, and actionable.*
