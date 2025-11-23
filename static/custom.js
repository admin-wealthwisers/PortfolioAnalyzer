/* ========================================
   WealthMisers Portfolio Analytics - Custom JavaScript
   Flip Cards, Drag/Resize, Animations
   ======================================== */

(function() {
    'use strict';
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    function init() {
        console.log('WealthMisers Custom JS initialized');
        
        // Initialize flip cards
        initFlipCards();
        
        // Initialize draggable cards
        initDraggableCards();
        
        // Initialize animations
        initAnimations();
        
        // Initialize modal
        initModal();
        
        // Initialize AI insights dismiss
        initAIInsights();
    }
    
    /* ========================================
       Flip Cards
       ======================================== */
    
    function initFlipCards() {
        // Add flip functionality to all flip cards
        const flipCards = document.querySelectorAll('.flip-card-container');
        
        flipCards.forEach(container => {
            const card = container.querySelector('.flip-card');
            if (card) {
                container.addEventListener('click', function(e) {
                    // Don't flip if clicking on interactive elements
                    if (e.target.closest('button, a, input')) {
                        return;
                    }
                    card.classList.toggle('flipped');
                });
            }
        });
    }
    
    // Flip card explanations (static content)
    const flipCardContent = {
        'risk-score': {
            title: '🎯 Risk Score Explained',
            content: `The Risk Score (0-10) is calculated using multiple factors:
            
            <ul style="text-align: left; margin: 1rem 0;">
                <li><strong>Volatility (30%):</strong> How much prices fluctuate</li>
                <li><strong>Beta (20%):</strong> Correlation with market movements</li>
                <li><strong>Diversification (30%):</strong> Spread across different stocks</li>
                <li><strong>Overlaps (20%):</strong> Family members holding same stocks</li>
            </ul>
            
            <p><strong>Lower scores (0-3):</strong> Conservative, stable portfolio</p>
            <p><strong>Medium scores (4-6):</strong> Balanced risk-reward</p>
            <p><strong>Higher scores (7-10):</strong> Aggressive, higher volatility</p>`
        },
        'sharpe-ratio': {
            title: '📊 Sharpe Ratio Explained',
            content: `The Sharpe Ratio measures risk-adjusted returns:
            
            <p style="margin: 1rem 0;"><strong>Formula:</strong> (Return - Risk-free Rate) / Volatility</p>
            
            <ul style="text-align: left; margin: 1rem 0;">
                <li><strong>&lt; 0:</strong> Losing money vs. risk-free investment</li>
                <li><strong>0 - 1:</strong> Suboptimal returns for the risk taken</li>
                <li><strong>1 - 2:</strong> Good risk-adjusted returns</li>
                <li><strong>&gt; 2:</strong> Excellent returns for the risk level</li>
            </ul>
            
            <p>A higher Sharpe ratio means you're getting more return per unit of risk.</p>`
        },
        'treemap': {
            title: '🗺️ Treemap Explained',
            content: `The Treemap visualizes your portfolio allocation:
            
            <ul style="text-align: left; margin: 1rem 0;">
                <li><strong>Size of boxes:</strong> Represents the value of each holding</li>
                <li><strong>Color intensity:</strong> Shows the weight/concentration</li>
                <li><strong>Labels:</strong> Stock symbol and current value</li>
            </ul>
            
            <p><strong>How to read it:</strong></p>
            <ul style="text-align: left;">
                <li>Larger boxes = More money invested</li>
                <li>Darker colors = Higher portfolio weight</li>
                <li>Click boxes to drill down into details</li>
            </ul>
            
            <p>Look for balance - no single box should dominate!</p>`
        },
        'diversification': {
            title: '🌈 Diversification Score Explained',
            content: `Diversification Score (0-10) measures portfolio spread:
            
            <ul style="text-align: left; margin: 1rem 0;">
                <li><strong>Number of holdings (50%):</strong> More stocks = better</li>
                <li><strong>Correlation (50%):</strong> How stocks move together</li>
            </ul>
            
            <p><strong>Score Interpretation:</strong></p>
            <ul style="text-align: left;">
                <li><strong>0-3:</strong> Poor diversification, concentrated risk</li>
                <li><strong>4-6:</strong> Moderate diversification</li>
                <li><strong>7-10:</strong> Well-diversified, reduced risk</li>
            </ul>
            
            <p>Ideal: 15-20 stocks across different sectors with low correlation.</p>`
        },
        'member-comparison': {
            title: '👥 Member Comparison Explained',
            content: `This chart compares family members' portfolios:
            
            <ul style="text-align: left; margin: 1rem 0;">
                <li><strong>Portfolio Value:</strong> Total investment per member</li>
                <li><strong>Gain %:</strong> Performance (green = profit, red = loss)</li>
            </ul>
            
            <p><strong>What to look for:</strong></p>
            <ul style="text-align: left;">
                <li>Balance in allocation across family</li>
                <li>Consistent positive returns</li>
                <li>Individual performance differences</li>
            </ul>
            
            <p>Use this to identify who might need portfolio rebalancing.</p>`
        },
        'overlap': {
            title: '⚠️ Overlap Detection Explained',
            content: `Stock overlaps represent concentration risk:
            
            <ul style="text-align: left; margin: 1rem 0;">
                <li><strong>Overlap:</strong> Same stock owned by multiple members</li>
                <li><strong>Risk:</strong> If that stock falls, entire family is affected</li>
            </ul>
            
            <p><strong>Why it matters:</strong></p>
            <ul style="text-align: left;">
                <li>Reduces family-level diversification</li>
                <li>Magnifies impact of single stock events</li>
                <li>Creates correlated losses</li>
            </ul>
            
            <p><strong>Solution:</strong> Coordinate holdings to reduce overlaps and spread risk across different stocks.</p>`
        }
    };
    
    /* ========================================
       Draggable & Resizable Cards
       ======================================== */
    
    function initDraggableCards() {
        const cards = document.querySelectorAll('.chart-card');
        
        cards.forEach(card => {
            // Add drag handle
            const header = card.querySelector('.chart-header');
            if (header) {
                header.style.cursor = 'move';
                makeDraggable(card, header);
            }
        });
    }
    
    function makeDraggable(element, handle) {
        let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
        
        handle.onmousedown = dragMouseDown;
        
        function dragMouseDown(e) {
            e.preventDefault();
            pos3 = e.clientX;
            pos4 = e.clientY;
            document.onmouseup = closeDragElement;
            document.onmousemove = elementDrag;
            element.classList.add('dragging');
        }
        
        function elementDrag(e) {
            e.preventDefault();
            pos1 = pos3 - e.clientX;
            pos2 = pos4 - e.clientY;
            pos3 = e.clientX;
            pos4 = e.clientY;
            
            element.style.position = 'relative';
            element.style.top = (element.offsetTop - pos2) + "px";
            element.style.left = (element.offsetLeft - pos1) + "px";
        }
        
        function closeDragElement() {
            document.onmouseup = null;
            document.onmousemove = null;
            element.classList.remove('dragging');
        }
    }
    
    /* ========================================
       Animations
       ======================================== */
    
    function initAnimations() {
        // Stagger animation for cards
        const cards = document.querySelectorAll('.metric-card, .flip-card-container');
        cards.forEach((card, index) => {
            card.style.animationDelay = `${index * 0.1}s`;
        });
        
        // Observe elements for fade-in on scroll
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in-up');
                }
            });
        }, { threshold: 0.1 });
        
        document.querySelectorAll('.chart-card').forEach(card => {
            observer.observe(card);
        });
    }
    
    // Animate gauge needle
    function animateGaugeNeedle(gaugeElement, targetValue, maxValue = 10) {
        const rotation = ((targetValue / maxValue) * 180) - 90; // -90 to 90 degrees
        gaugeElement.style.setProperty('--target-rotation', `${rotation}deg`);
        gaugeElement.style.animation = 'gaugeNeedle 2s ease-out forwards';
    }
    
    /* ========================================
       Modal
       ======================================== */
    
    function initModal() {
        // Modal open/close functionality
        window.openInputModal = function() {
            const modal = document.getElementById('input-modal');
            if (modal) {
                modal.classList.remove('hidden');
            }
        };
        
        window.closeInputModal = function() {
            const modal = document.getElementById('input-modal');
            if (modal) {
                modal.classList.add('hidden');
            }
        };
        
        // Close modal on overlay click
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('modal-overlay')) {
                closeInputModal();
            }
        });
        
        // Close modal on Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeInputModal();
            }
        });
    }
    
    /* ========================================
       AI Insights
       ======================================== */
    
    function initAIInsights() {
        // Dismiss AI insights
        window.dismissAIInsights = function() {
            const aiCard = document.getElementById('ai-insights-card');
            if (aiCard) {
                aiCard.style.animation = 'fadeOut 0.3s ease-out forwards';
                setTimeout(() => {
                    aiCard.classList.add('hidden');
                    // Show "Show Insights" button
                    const showBtn = document.getElementById('show-insights-btn');
                    if (showBtn) {
                        showBtn.classList.remove('hidden');
                    }
                }, 300);
            }
        };
        
        // Show AI insights
        window.showAIInsights = function() {
            const aiCard = document.getElementById('ai-insights-card');
            const showBtn = document.getElementById('show-insights-btn');
            
            if (aiCard) {
                aiCard.classList.remove('hidden');
                aiCard.style.animation = 'fadeInUp 0.5s ease-out forwards';
            }
            
            if (showBtn) {
                showBtn.classList.add('hidden');
            }
        };
    }
    
    /* ========================================
       Loading States
       ======================================== */
    
    function showLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = '<div class="loading-spinner"></div>';
        }
    }
    
    function hideLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = '';
        }
    }
    
    /* ========================================
       Utility Functions
       ======================================== */
    
    // Add CSS fadeOut animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeOut {
            from { opacity: 1; }
            to { opacity: 0; }
        }
    `;
    document.head.appendChild(style);
    
    // Export functions for use in Gradio
    window.WealthMisers = {
        animateGaugeNeedle,
        showLoading,
        hideLoading,
        flipCardContent
    };
    
})();
