"""
LLM Chat module for portfolio insights
Uses Anthropic Claude API
"""

import os
from typing import List, Dict, Optional

# Try to import anthropic
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: anthropic package not available. Install with: pip install anthropic")

from llm.context_builder import (
    build_portfolio_context,
    build_optimization_context,
    build_risk_context,
    get_system_prompt
)

# API configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "YOUR_API_KEY_HERE")
MODEL_NAME = "claude-sonnet-4-20250514"
MAX_TOKENS = 2000

class PortfolioChat:
    """Chat interface for portfolio insights using Claude API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize chat with API key"""
        self.api_key = api_key or ANTHROPIC_API_KEY
        
        if ANTHROPIC_AVAILABLE and self.api_key and self.api_key != "YOUR_API_KEY_HERE":
            self.client = Anthropic(api_key=self.api_key)
            self.is_configured = True
        else:
            self.client = None
            self.is_configured = False
        
        self.conversation_history = []
        self.portfolio_context = ""
        self.optimization_context = ""
        self.risk_context = ""
    
    def set_portfolio_data(self, portfolio_data):
        """Set portfolio data for context"""
        self.portfolio_context = build_portfolio_context(portfolio_data)
    
    def set_optimization_data(self, optimization_result):
        """Set optimization results for context"""
        self.optimization_context = build_optimization_context(optimization_result)
    
    def set_risk_data(self, risk_data):
        """Set risk analysis for context"""
        self.risk_context = build_risk_context(risk_data)
    
    def get_full_context(self):
        """Build full context from all available data"""
        context_parts = []
        
        if self.portfolio_context:
            context_parts.append(self.portfolio_context)
        
        if self.optimization_context:
            context_parts.append("\n" + self.optimization_context)
        
        if self.risk_context:
            context_parts.append("\n" + self.risk_context)
        
        return "\n\n".join(context_parts)
    
    def chat(self, user_message: str) -> str:
        """
        Send a message and get response from Claude
        
        Args:
            user_message: User's question/message
            
        Returns:
            Claude's response text
        """
        if not self.is_configured:
            return ("⚠️ Claude API is not configured. Please set your ANTHROPIC_API_KEY environment variable "
                   "or provide it in the settings. You can get an API key from: https://console.anthropic.com/")
        
        try:
            # Build messages
            messages = []
            
            # Add conversation history
            for msg in self.conversation_history:
                messages.append(msg)
            
            # Add current user message with context
            full_context = self.get_full_context()
            
            if full_context:
                user_content = f"""Portfolio Data Context:

{full_context}

---

User Question: {user_message}"""
            else:
                user_content = user_message
            
            messages.append({
                "role": "user",
                "content": user_content
            })
            
            # Call Claude API
            response = self.client.messages.create(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                system=get_system_prompt(),
                messages=messages
            )
            
            # Extract response text
            assistant_message = response.content[0].text
            
            # Update conversation history (without full context to save tokens)
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            # Keep only last 10 messages to avoid token limits
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            return assistant_message
            
        except Exception as e:
            return f"❌ Error communicating with Claude API: {str(e)}\n\nPlease check your API key and internet connection."
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def get_suggested_questions(self, portfolio_data):
        """Generate suggested questions based on portfolio analysis"""
        suggestions = []
        
        if not portfolio_data:
            return [
                "What should I consider when building a portfolio?",
                "How do I diversify my investments?",
                "What is a good Sharpe ratio?"
            ]
        
        family = portfolio_data['family']
        
        # Risk-based suggestions
        if family['risk_score'] > 6:
            suggestions.append("Why is my portfolio risk score high and how can I reduce it?")
        
        # Overlap suggestions
        if family['overlapping_stocks'] > 0:
            suggestions.append("What's the problem with overlapping holdings and how should we fix it?")
        
        # Diversification suggestions
        if family['metrics']['diversification_score'] < 5:
            suggestions.append("How can we improve our portfolio diversification?")
        
        # Performance suggestions
        if family['total_gain_pct'] < 0:
            suggestions.append("Our portfolio is down. What should we do?")
        elif family['total_gain_pct'] > 20:
            suggestions.append("Should we book profits or hold our positions?")
        
        # General suggestions
        suggestions.extend([
            "What are the strengths and weaknesses of our portfolio?",
            "Which member has the best portfolio allocation?",
            "Should we rebalance our portfolio?"
        ])
        
        return suggestions[:6]  # Return max 6 suggestions

# Global chat instance
chat_instance = None

def get_chat_instance(api_key: Optional[str] = None):
    """Get or create global chat instance"""
    global chat_instance
    
    if chat_instance is None or api_key:
        chat_instance = PortfolioChat(api_key)
    
    return chat_instance

def send_message(user_message: str, portfolio_data=None, optimization_result=None, risk_data=None, api_key: Optional[str] = None) -> str:
    """
    Convenience function to send a message
    
    Args:
        user_message: User's question
        portfolio_data: Portfolio data dict (optional)
        optimization_result: Optimization results (optional)
        risk_data: Risk analysis data (optional)
        api_key: API key (optional, uses env var if not provided)
        
    Returns:
        Response text
    """
    chat = get_chat_instance(api_key)
    
    # Update contexts if provided
    if portfolio_data:
        chat.set_portfolio_data(portfolio_data)
    
    if optimization_result:
        chat.set_optimization_data(optimization_result)
    
    if risk_data:
        chat.set_risk_data(risk_data)
    
    return chat.chat(user_message)
