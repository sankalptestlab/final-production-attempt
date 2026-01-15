import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Button, Card } from '../components/ui'
import './Track.css'

const mockApplication = {
    id: 'APP-2024-12345',
    status: 'in_progress',
    created_at: '2024-01-12T10:30:00',
    business_name: 'Tech Solutions Pvt Ltd',
    loan_amount: 45,
    selected_lender: 'HDFC Bank',
    timeline: [
        {
            status: 'completed',
            title: 'Application Submitted',
            description: 'Your application has been received',
            timestamp: '2024-01-12T10:30:00',
            icon: '✅'
        },
        {
            status: 'completed',
            title: 'Documents Verified',
            description: 'All documents have been verified',
            timestamp: '2024-01-12T11:15:00',
            icon: '📄'
        },
        {
            status: 'current',
            title: 'Credit Assessment',
            description: 'Lender is reviewing your credit profile',
            timestamp: null,
            icon: '🔍'
        },
        {
            status: 'pending',
            title: 'Approval Decision',
            description: 'Final approval from lender',
            timestamp: null,
            icon: '✍️'
        },
        {
            status: 'pending',
            title: 'Disbursement',
            description: 'Funds will be transferred to your account',
            timestamp: null,
            icon: '💰'
        }
    ],
    documents: [
        { name: 'GST Certificate', status: 'verified', icon: '📑' },
        { name: 'PAN Card', status: 'verified', icon: '📄' },
        { name: 'Bank Statement (6 months)', status: 'verified', icon: '🏦' },
        { name: 'Latest ITR', status: 'pending', icon: '📋' }
    ],
    messages: [
        {
            from: 'system',
            message: 'Welcome! Your application has been submitted successfully.',
            timestamp: '2024-01-12T10:30:00'
        },
        {
            from: 'agent',
            message: 'Hi! I\'m reviewing your application. Please upload your latest ITR to speed up the process.',
            timestamp: '2024-01-12T11:00:00'
        }
    ]
}

function Track() {
    const { id } = useParams()
    const [application, setApplication] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        // Simulate API call
        setTimeout(() => {
            setApplication(mockApplication)
            setLoading(false)
        }, 500)
    }, [id])

    if (loading) {
        return (
            <div className="track-page">
                <div className="container">
                    <div className="track-loading">
                        <div className="track-loading__spinner"></div>
                        <p>Loading application...</p>
                    </div>
                </div>
            </div>
        )
    }

    const formatDate = (dateStr) => {
        if (!dateStr) return ''
        const date = new Date(dateStr)
        return date.toLocaleDateString('en-IN', {
            day: 'numeric',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    return (
        <div className="track-page">
            <div className="container">
                {/* Header */}
                <div className="track-header">
                    <div className="track-header__info">
                        <h1>Track Your Application</h1>
                        <p className="track-header__id">Application ID: {application.id}</p>
                    </div>
                    <div className="track-header__status">
                        <span className={`status-badge status-badge--${application.status}`}>
                            🔄 In Progress
                        </span>
                    </div>
                </div>

                <div className="track-grid">
                    {/* Left Column: Timeline */}
                    <div className="track-main">
                        {/* Summary Card */}
                        <Card padding="lg" className="track-summary">
                            <div className="track-summary__grid">
                                <div className="track-summary__item">
                                    <span className="track-summary__label">Business</span>
                                    <strong className="track-summary__value">{application.business_name}</strong>
                                </div>
                                <div className="track-summary__item">
                                    <span className="track-summary__label">Loan Amount</span>
                                    <strong className="track-summary__value">₹{application.loan_amount}L</strong>
                                </div>
                                <div className="track-summary__item">
                                    <span className="track-summary__label">Lender</span>
                                    <strong className="track-summary__value">{application.selected_lender}</strong>
                                </div>
                                <div className="track-summary__item">
                                    <span className="track-summary__label">Applied On</span>
                                    <strong className="track-summary__value">{formatDate(application.created_at)}</strong>
                                </div>
                            </div>
                        </Card>

                        {/* Timeline */}
                        <Card padding="lg">
                            <h2 className="track-section-title">Application Timeline</h2>
                            <div className="timeline">
                                {application.timeline.map((step, index) => (
                                    <div
                                        key={index}
                                        className={`timeline__item timeline__item--${step.status}`}
                                    >
                                        <div className="timeline__icon">{step.icon}</div>
                                        <div className="timeline__content">
                                            <h4 className="timeline__title">{step.title}</h4>
                                            <p className="timeline__description">{step.description}</p>
                                            {step.timestamp && (
                                                <span className="timeline__time">{formatDate(step.timestamp)}</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </Card>
                    </div>

                    {/* Right Column: Documents & Messages */}
                    <div className="track-sidebar">
                        {/* Documents */}
                        <Card padding="lg">
                            <h3 className="track-section-title">Documents</h3>
                            <div className="documents-list">
                                {application.documents.map((doc, index) => (
                                    <div
                                        key={index}
                                        className={`document-item document-item--${doc.status}`}
                                    >
                                        <span className="document-item__icon">{doc.icon}</span>
                                        <span className="document-item__name">{doc.name}</span>
                                        <span className={`document-item__status document-item__status--${doc.status}`}>
                                            {doc.status === 'verified' ? '✓ Verified' : '⏳ Pending'}
                                        </span>
                                    </div>
                                ))}
                            </div>
                            <Button variant="secondary" size="sm" fullWidth>
                                + Upload Document
                            </Button>
                        </Card>

                        {/* Messages */}
                        <Card padding="lg">
                            <h3 className="track-section-title">Messages</h3>
                            <div className="messages-list">
                                {application.messages.map((msg, index) => (
                                    <div key={index} className={`message message--${msg.from}`}>
                                        <div className="message__content">{msg.message}</div>
                                        <span className="message__time">{formatDate(msg.timestamp)}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="message-input">
                                <input
                                    type="text"
                                    placeholder="Type a message..."
                                    className="message-input__field"
                                />
                                <Button size="sm">Send</Button>
                            </div>
                        </Card>

                        {/* Help */}
                        <Card padding="md" variant="outlined">
                            <div className="help-card">
                                <span className="help-card__icon">💬</span>
                                <div>
                                    <strong>Need Help?</strong>
                                    <p>Our team is available Mon-Sat, 9AM-6PM</p>
                                    <a href="tel:+919876543210">📞 Call Us</a>
                                </div>
                            </div>
                        </Card>
                    </div>
                </div>

                {/* Actions */}
                <div className="track-actions">
                    <Link to="/results/demo-123">
                        <Button variant="secondary" size="lg">
                            ← Back to Results
                        </Button>
                    </Link>
                    <Button variant="primary" size="lg">
                        📞 Contact Support
                    </Button>
                </div>
            </div>
        </div>
    )
}

export default Track
