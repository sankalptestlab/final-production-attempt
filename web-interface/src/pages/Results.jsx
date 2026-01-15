import { useState, useEffect } from 'react'
import { Link, useParams, useLocation } from 'react-router-dom'
import { Button, Card } from '../components/ui'
import './Results.css'

function LenderCard({ lender, isRecommended }) {
    const [expanded, setExpanded] = useState(false)

    return (
        <Card
            variant={isRecommended ? 'elevated' : 'default'}
            className={`lender-card ${isRecommended ? 'lender-card--recommended' : ''} ${lender.is_scf ? 'lender-card--scf' : ''}`}
        >
            {isRecommended && (
                <div className="lender-card__badge">⭐ Best Match</div>
            )}
            {lender.is_scf && !isRecommended && (
                <div className="lender-card__badge lender-card__badge--scf">📜 Invoice Discounting</div>
            )}

            <div className="lender-card__header">
                <div className="lender-card__logo">
                    {lender.is_scf ? '📜' : '🏦'}
                </div>
                <div className="lender-card__info">
                    <h3 className="lender-card__name">{lender.lender_name}</h3>
                    <span className="lender-card__product">{lender.product}</span>
                </div>
            </div>

            <div className="lender-card__stats">
                <div className="lender-card__stat">
                    <span className="lender-card__stat-label">Amount</span>
                    <span className="lender-card__stat-value">₹{lender.eligible_amount_lakhs}L</span>
                </div>
                <div className="lender-card__stat">
                    <span className="lender-card__stat-label">Interest</span>
                    <span className="lender-card__stat-value">{lender.interest_rate_range}</span>
                </div>
                <div className="lender-card__stat">
                    <span className="lender-card__stat-label">Tenure</span>
                    <span className="lender-card__stat-value">{lender.tenure_months} months</span>
                </div>
            </div>

            <div className="lender-card__probability">
                <div className="lender-card__probability-bar">
                    <div
                        className="lender-card__probability-fill"
                        style={{ width: `${lender.approval_probability * 100}%` }}
                    ></div>
                </div>
                <span className="lender-card__probability-text">
                    {Math.round(lender.approval_probability * 100)}% approval chance
                </span>
            </div>

            <button
                className="lender-card__expand"
                onClick={() => setExpanded(!expanded)}
            >
                {expanded ? 'Hide Details ↑' : 'View Requirements ↓'}
            </button>

            {expanded && (
                <div className="lender-card__details">
                    <h4>Documents Required:</h4>
                    <ul>
                        {lender.requirements.map((req, i) => (
                            <li key={i}>📄 {req}</li>
                        ))}
                    </ul>
                </div>
            )}

            <div className="lender-card__actions">
                <Button variant="secondary" size="md">
                    Compare
                </Button>
                <Button variant={isRecommended ? 'accent' : 'primary'} size="md">
                    Apply Now →
                </Button>
            </div>
        </Card>
    )
}

function Results() {
    const { id } = useParams()
    const location = useLocation()
    const [results, setResults] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        // Try to get results from navigation state first, then localStorage
        const stateResult = location.state?.result
        if (stateResult) {
            setResults(stateResult)
            setLoading(false)
            return
        }

        // Try localStorage as fallback
        const storedResult = localStorage.getItem('loanApplicationResult')
        if (storedResult) {
            try {
                const parsed = JSON.parse(storedResult)
                setResults(parsed)
                setLoading(false)
                return
            } catch (e) {
                console.error('Failed to parse stored result:', e)
            }
        }

        // If no data found, show error state
        setLoading(false)
    }, [id, location.state])

    if (loading) {
        return (
            <div className="results-page">
                <div className="container">
                    <div className="results-loading">
                        <div className="results-loading__spinner"></div>
                        <p>Loading your results...</p>
                    </div>
                </div>
            </div>
        )
    }

    if (!results) {
        return (
            <div className="results-page">
                <div className="container">
                    <div className="results-error">
                        <h2>No Results Found</h2>
                        <p>We couldn't find your application results. Please try submitting a new application.</p>
                        <Link to="/apply">
                            <Button variant="primary" size="lg">Start New Application</Button>
                        </Link>
                    </div>
                </div>
            </div>
        )
    }

    const scfOffers = (results.lender_matches || []).filter(l => l.is_scf)
    const regularOffers = (results.lender_matches || []).filter(l => !l.is_scf)

    return (
        <div className="results-page">
            <div className="container">
                {/* Header */}
                <div className="results-header">
                    <div className="results-header__content">
                        <h1>🎉 Great News, {results.business_name}!</h1>
                        <p>Based on your profile, you're eligible for multiple loan options.</p>
                    </div>
                </div>

                {/* Summary Cards */}
                <div className="results-summary">
                    <Card variant="success" padding="md" className="summary-card">
                        <div className="summary-card__icon">✅</div>
                        <div className="summary-card__content">
                            <span className="summary-card__label">Eligibility</span>
                            <strong className="summary-card__value summary-card__value--success">
                                {results.overall_eligibility.toUpperCase()}
                            </strong>
                        </div>
                    </Card>

                    <Card variant="elevated" padding="md" className="summary-card">
                        <div className="summary-card__icon">💰</div>
                        <div className="summary-card__content">
                            <span className="summary-card__label">Max Amount</span>
                            <strong className="summary-card__value">₹{results.max_eligible_amount_lakhs}L</strong>
                        </div>
                    </Card>

                    <Card variant="elevated" padding="md" className="summary-card">
                        <div className="summary-card__icon">📊</div>
                        <div className="summary-card__content">
                            <span className="summary-card__label">Credit Score</span>
                            <strong className="summary-card__value">{results.credit_score}</strong>
                        </div>
                    </Card>

                    <Card variant="elevated" padding="md" className="summary-card">
                        <div className="summary-card__icon">🏦</div>
                        <div className="summary-card__content">
                            <span className="summary-card__label">Offers</span>
                            <strong className="summary-card__value">{results.lender_matches.length} Lenders</strong>
                        </div>
                    </Card>
                </div>

                {/* Profile Insights */}
                <div className="results-insights">
                    <Card padding="lg">
                        <h2 className="results-section-title">Your Credit Profile Insights</h2>
                        <div className="insights-grid">
                            <div className="insights-column">
                                <h4 className="insights-heading insights-heading--success">
                                    ✅ Your Strengths
                                </h4>
                                <ul className="insights-list">
                                    {results.strengths.map((item, i) => (
                                        <li key={i}>{item}</li>
                                    ))}
                                </ul>
                            </div>
                            <div className="insights-column">
                                <h4 className="insights-heading insights-heading--warning">
                                    💡 Areas to Improve
                                </h4>
                                <ul className="insights-list">
                                    {results.improvements.map((item, i) => (
                                        <li key={i}>{item}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </Card>
                </div>

                {/* SCF Offers (if any) */}
                {scfOffers.length > 0 && (
                    <div className="results-section">
                        <div className="results-section-header">
                            <h2 className="results-section-title">
                                🚀 Special: Invoice Discounting Offers
                            </h2>
                            <p className="results-section-subtitle">
                                We found strong relationships with your partners (Anchors).
                                Get funds against your invoices at much lower rates!
                            </p>
                        </div>
                        <div className="lender-grid">
                            {scfOffers.map((lender, index) => (
                                <LenderCard
                                    key={lender.lender_id}
                                    lender={lender}
                                    isRecommended={index === 0}
                                />
                            ))}
                        </div>
                    </div>
                )}

                {/* Regular Offers */}
                <div className="results-section">
                    <div className="results-section-header">
                        <h2 className="results-section-title">
                            🏦 Business Loan Options
                        </h2>
                        <p className="results-section-subtitle">
                            Compare offers from our partner lenders
                        </p>
                    </div>
                    <div className="lender-grid">
                        {regularOffers.map((lender, index) => (
                            <LenderCard
                                key={lender.lender_id}
                                lender={lender}
                                isRecommended={scfOffers.length === 0 && index === 0}
                            />
                        ))}
                    </div>
                </div>

                {/* Next Steps */}
                <div className="results-section">
                    <Card variant="elevated" padding="lg" className="next-steps-card">
                        <h2 className="results-section-title">📋 Next Steps</h2>
                        <div className="next-steps-list">
                            <div className="next-step">
                                <div className="next-step__number">1</div>
                                <div className="next-step__content">
                                    <strong>Review & Compare</strong>
                                    <p>Compare the offers above and choose the one that best fits your needs</p>
                                </div>
                            </div>
                            <div className="next-step">
                                <div className="next-step__number">2</div>
                                <div className="next-step__content">
                                    <strong>Prepare Documents</strong>
                                    <p>Gather required documents like bank statements, ITR, and GST certificate</p>
                                </div>
                            </div>
                            <div className="next-step">
                                <div className="next-step__number">3</div>
                                <div className="next-step__content">
                                    <strong>Apply & Track</strong>
                                    <p>Submit your application and track the progress in real-time</p>
                                </div>
                            </div>
                        </div>
                    </Card>
                </div>

                {/* Actions */}
                <div className="results-actions">
                    <Button variant="secondary" size="lg">
                        📥 Download Report
                    </Button>
                    <Link to={`/track/${id}`}>
                        <Button variant="primary" size="lg">
                            Track Application →
                        </Button>
                    </Link>
                </div>
            </div>
        </div>
    )
}

export default Results
