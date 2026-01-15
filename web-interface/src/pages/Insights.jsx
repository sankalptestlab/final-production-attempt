import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Card } from '../components/ui'
import './Insights.css'

// Mock document analysis data - simulating what our AI extracts
const mockDocumentAnalysis = {
    gstin: '27AABCS1429B1ZB',
    business_name: 'Sharma Textiles Pvt Ltd',
    analysis_status: 'complete',
    documents_analyzed: [
        { type: 'GST Returns', count: 24, period: 'Apr 2022 - Mar 2024' },
        { type: 'Bank Statements', count: 12, period: 'Jan 2024 - Dec 2024' },
        { type: 'Credit Bureau', count: 2, period: 'Commercial + Consumer' },
        { type: 'ITR', count: 2, period: 'FY 2022-23, 2023-24' }
    ],
    extracted_insights: {
        revenue_trend: {
            title: 'Revenue Growth Detected',
            icon: '📈',
            insight: 'Your business shows 18% YoY growth based on GST sales data.',
            data_points: [
                { label: 'FY 2022-23', value: '₹2.8 Cr' },
                { label: 'FY 2023-24', value: '₹3.3 Cr' },
                { label: 'Trend', value: '+18%' }
            ],
            impact: 'positive',
            recommendation: 'Strong growth trajectory qualifies you for growth-focused lending products with favorable terms.'
        },
        credit_health: {
            title: 'Excellent Credit Profile',
            icon: '✅',
            insight: 'CMR-2 rating with zero defaults in 36 months.',
            data_points: [
                { label: 'Credit Score', value: 'CMR-2' },
                { label: 'Max DPD', value: '0 days' },
                { label: 'Utilization', value: '45%' }
            ],
            impact: 'positive',
            recommendation: 'Your pristine credit history qualifies you for the lowest interest rates in the market.'
        },
        cash_flow: {
            title: 'Strong Cash Flow Pattern',
            icon: '💰',
            insight: 'Consistent monthly inflows averaging ₹28L with low variance.',
            data_points: [
                { label: 'Avg Monthly', value: '₹28L' },
                { label: 'Peak Month', value: '₹42L' },
                { label: 'Variance', value: 'Low' }
            ],
            impact: 'positive',
            recommendation: 'Predictable cash flows make you ideal for EMI-based products.'
        },
        anchor_opportunity: {
            title: 'SCF Opportunity Identified!',
            icon: '🏢',
            insight: 'We detected high concentration with 2 major customers (55% of sales).',
            data_points: [
                { label: 'Top Customer', value: '35% share' },
                { label: '2nd Customer', value: '20% share' },
                { label: 'Consistency', value: '24 months' }
            ],
            impact: 'opportunity',
            recommendation: 'You qualify for Invoice Discounting at rates 40% lower than regular loans!'
        },
        seasonality: {
            title: 'Seasonal Pattern Detected',
            icon: '📅',
            insight: 'Sales peak in Oct-Dec (Diwali season) and dip in Apr-Jun.',
            data_points: [
                { label: 'Peak Quarter', value: 'Q3 (Oct-Dec)' },
                { label: 'Low Quarter', value: 'Q1 (Apr-Jun)' },
                { label: 'Variation', value: '±25%' }
            ],
            impact: 'neutral',
            recommendation: 'We\'ll recommend products with flexible EMI options for seasonal businesses.'
        },
        compliance: {
            title: 'Filing Discipline',
            icon: '📋',
            insight: '98% on-time GST filing rate over 24 months.',
            data_points: [
                { label: 'On-time filings', value: '23/24' },
                { label: 'Late filings', value: '1' },
                { label: 'NIL returns', value: '0' }
            ],
            impact: 'positive',
            recommendation: 'Strong compliance record unlocks premium lender options.'
        }
    },
    tailor_made_products: [
        {
            id: 'scf_sid',
            name: 'Invoice Discounting',
            tagline: 'Turn pending invoices into instant cash',
            why_for_you: 'Your high concentration with corporate buyers makes you perfect for this.',
            amount: '₹24.75L',
            rate: '1.1% per month',
            tenure: '90 days',
            savings: '₹45,000/year vs regular loan',
            match_score: 95,
            icon: '📜',
            color: 'accent'
        },
        {
            id: 'working_capital',
            name: 'Flexi Working Capital',
            tagline: 'Seasonal flexibility built-in',
            why_for_you: 'Designed for seasonal businesses like yours - pay less in off-season.',
            amount: '₹35L',
            rate: '12.5% p.a.',
            tenure: '24 months',
            savings: 'Flexible EMI saves ₹30,000/year',
            match_score: 88,
            icon: '🔄',
            color: 'primary'
        },
        {
            id: 'growth_loan',
            name: 'Growth Accelerator',
            tagline: 'For businesses on the rise',
            why_for_you: 'Your 18% growth rate qualifies you for growth-focused products.',
            amount: '₹45L',
            rate: '11.5% p.a.',
            tenure: '36 months',
            savings: 'Approved for ₹10L more than average',
            match_score: 82,
            icon: '🚀',
            color: 'success'
        }
    ]
}

function InsightCard({ insight }) {
    const [expanded, setExpanded] = useState(false)

    return (
        <Card
            className={`insight-card insight-card--${insight.impact}`}
            padding="md"
        >
            <div className="insight-card__header">
                <span className="insight-card__icon">{insight.icon}</span>
                <h4 className="insight-card__title">{insight.title}</h4>
            </div>
            <p className="insight-card__insight">{insight.insight}</p>

            <div className="insight-card__data">
                {insight.data_points.map((dp, i) => (
                    <div key={i} className="insight-card__data-point">
                        <span className="insight-card__data-label">{dp.label}</span>
                        <strong className="insight-card__data-value">{dp.value}</strong>
                    </div>
                ))}
            </div>

            <button
                className="insight-card__toggle"
                onClick={() => setExpanded(!expanded)}
            >
                {expanded ? 'Hide recommendation' : 'How does this help me?'}
            </button>

            {expanded && (
                <div className="insight-card__recommendation">
                    <span className="insight-card__rec-icon">💡</span>
                    <p>{insight.recommendation}</p>
                </div>
            )}
        </Card>
    )
}

function ProductCard({ product }) {
    return (
        <Card
            className={`product-card product-card--${product.color}`}
            padding="lg"
            hover
        >
            <div className="product-card__match">
                <span className="product-card__match-score">{product.match_score}%</span>
                <span className="product-card__match-label">match</span>
            </div>

            <div className="product-card__icon">{product.icon}</div>
            <h3 className="product-card__name">{product.name}</h3>
            <p className="product-card__tagline">{product.tagline}</p>

            <div className="product-card__why">
                <span className="product-card__why-label">Why this is for you:</span>
                <p className="product-card__why-text">{product.why_for_you}</p>
            </div>

            <div className="product-card__terms">
                <div className="product-card__term">
                    <span>Amount</span>
                    <strong>{product.amount}</strong>
                </div>
                <div className="product-card__term">
                    <span>Rate</span>
                    <strong>{product.rate}</strong>
                </div>
                <div className="product-card__term">
                    <span>Tenure</span>
                    <strong>{product.tenure}</strong>
                </div>
            </div>

            <div className="product-card__savings">
                ✨ {product.savings}
            </div>

            <Button variant={product.color === 'accent' ? 'accent' : 'primary'} fullWidth>
                Apply for {product.name} →
            </Button>
        </Card>
    )
}

function Insights() {
    const [analysisStep, setAnalysisStep] = useState(0)
    const [showInsights, setShowInsights] = useState(false)
    const data = mockDocumentAnalysis

    // Simulate progressive analysis
    useEffect(() => {
        if (analysisStep < 4) {
            const timer = setTimeout(() => {
                setAnalysisStep(prev => prev + 1)
            }, 800)
            return () => clearTimeout(timer)
        } else {
            setTimeout(() => setShowInsights(true), 500)
        }
    }, [analysisStep])

    return (
        <div className="insights-page">
            {/* Hero */}
            <section className="insights-hero">
                <div className="container">
                    <div className="insights-hero__content">
                        <h1>
                            <span className="insights-hero__subtitle">We Read Your Documents.</span>
                            <span className="insights-hero__title">We Understand Your Business.</span>
                        </h1>
                        <p className="insights-hero__description">
                            Our AI analyzes 40+ data points from your GST returns, bank statements,
                            and credit history to create lending products tailor-made for YOUR business.
                        </p>
                    </div>
                </div>
            </section>

            <div className="container">
                {/* Document Analysis Progress */}
                <section className="analysis-section">
                    <Card padding="lg" variant="elevated">
                        <div className="analysis-header">
                            <h2>📄 Documents Analyzed for {data.business_name}</h2>
                            <span className="analysis-gstin">GSTIN: {data.gstin}</span>
                        </div>

                        <div className="analysis-grid">
                            {data.documents_analyzed.map((doc, index) => (
                                <div
                                    key={index}
                                    className={`analysis-item ${index < analysisStep ? 'analysis-item--complete' : ''}`}
                                >
                                    <div className="analysis-item__icon">
                                        {index < analysisStep ? '✅' : '⏳'}
                                    </div>
                                    <div className="analysis-item__info">
                                        <strong>{doc.type}</strong>
                                        <span>{doc.count} documents • {doc.period}</span>
                                    </div>
                                    {index < analysisStep && (
                                        <div className="analysis-item__check">Analyzed</div>
                                    )}
                                </div>
                            ))}
                        </div>

                        {analysisStep < 4 && (
                            <div className="analysis-progress">
                                <div className="analysis-progress__bar">
                                    <div
                                        className="analysis-progress__fill"
                                        style={{ width: `${(analysisStep / 4) * 100}%` }}
                                    ></div>
                                </div>
                                <span className="analysis-progress__text">
                                    Analyzing {data.documents_analyzed[analysisStep]?.type}...
                                </span>
                            </div>
                        )}
                    </Card>
                </section>

                {showInsights && (
                    <>
                        {/* Extracted Insights */}
                        <section className="insights-section">
                            <div className="section-header">
                                <h2>🔍 What We Discovered About Your Business</h2>
                                <p>Our AI extracted these insights from your documents to build your personalized profile.</p>
                            </div>

                            <div className="insights-grid">
                                {Object.values(data.extracted_insights).map((insight, index) => (
                                    <InsightCard key={index} insight={insight} />
                                ))}
                            </div>
                        </section>

                        {/* Tailor-Made Products */}
                        <section className="products-section">
                            <div className="section-header">
                                <h2>🎯 Products Designed Just For You</h2>
                                <p>Based on your unique business profile, here are products crafted specifically for your needs.</p>
                            </div>

                            <div className="products-grid">
                                {data.tailor_made_products.map((product, index) => (
                                    <ProductCard key={index} product={product} />
                                ))}
                            </div>
                        </section>

                        {/* Comparison */}
                        <section className="comparison-section">
                            <Card padding="lg" variant="elevated">
                                <h2>💡 The Udyog Saathi Difference</h2>
                                <div className="comparison-grid">
                                    <div className="comparison-column comparison-column--others">
                                        <h4>❌ Other Platforms</h4>
                                        <ul>
                                            <li>One-size-fits-all products</li>
                                            <li>Fixed EMI regardless of business cycle</li>
                                            <li>Same rate for everyone</li>
                                            <li>Manual document verification</li>
                                            <li>Days to process</li>
                                        </ul>
                                    </div>
                                    <div className="comparison-column comparison-column--us">
                                        <h4>✅ Udyog Saathi</h4>
                                        <ul>
                                            <li>Products tailor-made for YOUR business</li>
                                            <li>Flexi EMI for seasonal patterns</li>
                                            <li>Better rates for proven compliance</li>
                                            <li>AI-powered instant analysis</li>
                                            <li>Minutes to eligible products</li>
                                        </ul>
                                    </div>
                                </div>
                            </Card>
                        </section>

                        {/* CTA */}
                        <section className="insights-cta">
                            <Card padding="lg" className="insights-cta__card">
                                <h2>Ready to Get Your Personalized Products?</h2>
                                <p>Enter your GST number and let our AI build your custom lending profile.</p>
                                <Link to="/apply">
                                    <Button size="lg" variant="accent">
                                        Get My Personalized Products →
                                    </Button>
                                </Link>
                            </Card>
                        </section>
                    </>
                )}
            </div>
        </div>
    )
}

export default Insights
