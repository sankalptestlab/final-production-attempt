import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card } from '../components/ui'
import './DSA.css'

// Mock data for DSA dashboard
const mockDSAData = {
    agent: {
        name: 'Rajesh Kumar',
        id: 'DSA-2024-1234',
        level: 'Gold Partner',
        commission_earned: 125000,
        commission_pending: 45000,
        leads_this_month: 28,
        conversion_rate: 0.42
    },
    stats: {
        total_leads: 156,
        approved: 65,
        pending: 23,
        rejected: 18,
        disbursed: 50
    },
    recent_applications: [
        {
            id: 'APP-2024-001',
            business_name: 'Sharma Textiles',
            gst: '27AABCS1429B1ZB',
            amount: 35,
            status: 'approved',
            date: '2024-01-12',
            lender: 'HDFC Bank',
            commission: 8750
        },
        {
            id: 'APP-2024-002',
            business_name: 'Tech Innovators LLP',
            gst: '29AABCT8765A1ZM',
            amount: 50,
            status: 'pending',
            date: '2024-01-11',
            lender: 'ICICI Bank',
            commission: null
        },
        {
            id: 'APP-2024-003',
            business_name: 'Green Foods Pvt Ltd',
            gst: '33AABCG2345H1ZP',
            amount: 25,
            status: 'disbursed',
            date: '2024-01-10',
            lender: 'Bajaj Finserv',
            commission: 6250
        },
        {
            id: 'APP-2024-004',
            business_name: 'Metro Auto Parts',
            gst: '27AABCM9876C1ZQ',
            amount: 15,
            status: 'rejected',
            date: '2024-01-09',
            lender: 'UGRO Capital',
            commission: null
        },
        {
            id: 'APP-2024-005',
            business_name: 'Sunrise Exports',
            gst: '32AABCS5432D1ZR',
            amount: 75,
            status: 'processing',
            date: '2024-01-08',
            lender: 'HDFC Bank',
            commission: null
        }
    ],
    performance: {
        monthly: [
            { month: 'Aug', leads: 18, approved: 8 },
            { month: 'Sep', leads: 22, approved: 10 },
            { month: 'Oct', leads: 25, approved: 12 },
            { month: 'Nov', leads: 30, approved: 14 },
            { month: 'Dec', leads: 28, approved: 13 },
            { month: 'Jan', leads: 28, approved: 8 }
        ]
    }
}

function StatCard({ icon, label, value, subvalue, trend }) {
    return (
        <Card padding="md" className="stat-card">
            <div className="stat-card__icon">{icon}</div>
            <div className="stat-card__content">
                <span className="stat-card__label">{label}</span>
                <strong className="stat-card__value">{value}</strong>
                {subvalue && <span className="stat-card__subvalue">{subvalue}</span>}
                {trend && (
                    <span className={`stat-card__trend stat-card__trend--${trend > 0 ? 'up' : 'down'}`}>
                        {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
                    </span>
                )}
            </div>
        </Card>
    )
}

function ApplicationRow({ app }) {
    const statusColors = {
        approved: 'success',
        pending: 'warning',
        processing: 'info',
        rejected: 'error',
        disbursed: 'success'
    }

    return (
        <tr className="app-row">
            <td>
                <Link to={`/dsa/application/${app.id}`} className="app-row__id">
                    {app.id}
                </Link>
            </td>
            <td>
                <div className="app-row__business">
                    <strong>{app.business_name}</strong>
                    <span>{app.gst}</span>
                </div>
            </td>
            <td className="app-row__amount">₹{app.amount}L</td>
            <td>{app.lender}</td>
            <td>
                <span className={`status-pill status-pill--${statusColors[app.status]}`}>
                    {app.status}
                </span>
            </td>
            <td className="app-row__commission">
                {app.commission ? `₹${app.commission.toLocaleString()}` : '-'}
            </td>
            <td>
                <Button variant="ghost" size="sm">View →</Button>
            </td>
        </tr>
    )
}

function DSA() {
    const [activeTab, setActiveTab] = useState('overview')
    const { agent, stats, recent_applications, performance } = mockDSAData

    return (
        <div className="dsa-page">
            {/* Header */}
            <div className="dsa-header">
                <div className="container">
                    <div className="dsa-header__content">
                        <div className="dsa-header__left">
                            <h1>DSA Dashboard</h1>
                            <p>Welcome back, {agent.name}</p>
                        </div>
                        <div className="dsa-header__right">
                            <div className="dsa-header__agent-info">
                                <span className="dsa-header__agent-id">{agent.id}</span>
                                <span className="dsa-header__agent-level">⭐ {agent.level}</span>
                            </div>
                            <Link to="/apply">
                                <Button variant="primary" size="md" icon="➕">
                                    New Application
                                </Button>
                            </Link>
                        </div>
                    </div>
                </div>
            </div>

            <div className="container">
                {/* Stats Grid */}
                <div className="dsa-stats">
                    <StatCard
                        icon="💰"
                        label="Commission Earned"
                        value={`₹${(agent.commission_earned / 1000).toFixed(0)}K`}
                        subvalue="This month"
                        trend={12}
                    />
                    <StatCard
                        icon="⏳"
                        label="Pending Payout"
                        value={`₹${(agent.commission_pending / 1000).toFixed(0)}K`}
                        subvalue="Processing"
                    />
                    <StatCard
                        icon="📊"
                        label="Conversion Rate"
                        value={`${(agent.conversion_rate * 100).toFixed(0)}%`}
                        subvalue="Industry avg: 35%"
                        trend={8}
                    />
                    <StatCard
                        icon="📈"
                        label="Leads This Month"
                        value={agent.leads_this_month}
                        subvalue="vs 25 last month"
                        trend={12}
                    />
                </div>

                {/* Tabs */}
                <div className="dsa-tabs">
                    <button
                        className={`dsa-tab ${activeTab === 'overview' ? 'dsa-tab--active' : ''}`}
                        onClick={() => setActiveTab('overview')}
                    >
                        Overview
                    </button>
                    <button
                        className={`dsa-tab ${activeTab === 'applications' ? 'dsa-tab--active' : ''}`}
                        onClick={() => setActiveTab('applications')}
                    >
                        Applications ({stats.total_leads})
                    </button>
                    <button
                        className={`dsa-tab ${activeTab === 'payouts' ? 'dsa-tab--active' : ''}`}
                        onClick={() => setActiveTab('payouts')}
                    >
                        Payouts
                    </button>
                </div>

                {activeTab === 'overview' && (
                    <div className="dsa-content">
                        {/* Pipeline */}
                        <Card padding="lg" className="dsa-pipeline">
                            <h3>Application Pipeline</h3>
                            <div className="pipeline">
                                <div className="pipeline__stage">
                                    <div className="pipeline__count">{stats.total_leads}</div>
                                    <div className="pipeline__label">Total Leads</div>
                                </div>
                                <div className="pipeline__arrow">→</div>
                                <div className="pipeline__stage pipeline__stage--pending">
                                    <div className="pipeline__count">{stats.pending}</div>
                                    <div className="pipeline__label">Pending</div>
                                </div>
                                <div className="pipeline__arrow">→</div>
                                <div className="pipeline__stage pipeline__stage--approved">
                                    <div className="pipeline__count">{stats.approved}</div>
                                    <div className="pipeline__label">Approved</div>
                                </div>
                                <div className="pipeline__arrow">→</div>
                                <div className="pipeline__stage pipeline__stage--disbursed">
                                    <div className="pipeline__count">{stats.disbursed}</div>
                                    <div className="pipeline__label">Disbursed</div>
                                </div>
                            </div>
                        </Card>

                        {/* Recent Applications */}
                        <Card padding="lg" className="dsa-applications">
                            <div className="dsa-section-header">
                                <h3>Recent Applications</h3>
                                <Button variant="ghost" size="sm" onClick={() => setActiveTab('applications')}>
                                    View All →
                                </Button>
                            </div>
                            <div className="table-wrapper">
                                <table className="dsa-table">
                                    <thead>
                                        <tr>
                                            <th>ID</th>
                                            <th>Business</th>
                                            <th>Amount</th>
                                            <th>Lender</th>
                                            <th>Status</th>
                                            <th>Commission</th>
                                            <th></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {recent_applications.slice(0, 5).map(app => (
                                            <ApplicationRow key={app.id} app={app} />
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </Card>

                        {/* Quick Actions */}
                        <div className="dsa-quick-actions">
                            <Card padding="md" hover className="quick-action">
                                <span className="quick-action__icon">📝</span>
                                <strong>New Lead</strong>
                                <p>Submit a new loan application</p>
                            </Card>
                            <Card padding="md" hover className="quick-action">
                                <span className="quick-action__icon">📊</span>
                                <strong>Check Eligibility</strong>
                                <p>Quick GST-based eligibility check</p>
                            </Card>
                            <Card padding="md" hover className="quick-action">
                                <span className="quick-action__icon">📋</span>
                                <strong>Pending Docs</strong>
                                <p>View applications needing documents</p>
                            </Card>
                            <Card padding="md" hover className="quick-action">
                                <span className="quick-action__icon">💬</span>
                                <strong>Support</strong>
                                <p>Get help from our team</p>
                            </Card>
                        </div>
                    </div>
                )}

                {activeTab === 'applications' && (
                    <Card padding="lg" className="dsa-applications">
                        <div className="dsa-section-header">
                            <h3>All Applications</h3>
                            <div className="dsa-filters">
                                <select className="dsa-filter">
                                    <option>All Status</option>
                                    <option>Pending</option>
                                    <option>Approved</option>
                                    <option>Disbursed</option>
                                    <option>Rejected</option>
                                </select>
                                <select className="dsa-filter">
                                    <option>All Lenders</option>
                                    <option>HDFC Bank</option>
                                    <option>ICICI Bank</option>
                                    <option>Bajaj Finserv</option>
                                </select>
                            </div>
                        </div>
                        <div className="table-wrapper">
                            <table className="dsa-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Business</th>
                                        <th>Amount</th>
                                        <th>Lender</th>
                                        <th>Status</th>
                                        <th>Commission</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {recent_applications.map(app => (
                                        <ApplicationRow key={app.id} app={app} />
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </Card>
                )}

                {activeTab === 'payouts' && (
                    <div className="dsa-payouts">
                        <Card padding="lg">
                            <h3>Commission Summary</h3>
                            <div className="payout-summary">
                                <div className="payout-item">
                                    <span className="payout-item__label">Total Earned (All Time)</span>
                                    <strong className="payout-item__value">₹4,85,000</strong>
                                </div>
                                <div className="payout-item">
                                    <span className="payout-item__label">Paid Out</span>
                                    <strong className="payout-item__value payout-item__value--success">₹4,40,000</strong>
                                </div>
                                <div className="payout-item">
                                    <span className="payout-item__label">Pending Payout</span>
                                    <strong className="payout-item__value payout-item__value--warning">₹45,000</strong>
                                </div>
                            </div>
                        </Card>

                        <Card padding="lg">
                            <h3>Recent Payouts</h3>
                            <div className="payout-history">
                                <div className="payout-entry">
                                    <div className="payout-entry__info">
                                        <strong>December 2023 Payout</strong>
                                        <span>15 applications • Paid on Jan 5, 2024</span>
                                    </div>
                                    <div className="payout-entry__amount">₹65,000</div>
                                    <span className="status-pill status-pill--success">Paid</span>
                                </div>
                                <div className="payout-entry">
                                    <div className="payout-entry__info">
                                        <strong>November 2023 Payout</strong>
                                        <span>12 applications • Paid on Dec 5, 2023</span>
                                    </div>
                                    <div className="payout-entry__amount">₹52,000</div>
                                    <span className="status-pill status-pill--success">Paid</span>
                                </div>
                                <div className="payout-entry">
                                    <div className="payout-entry__info">
                                        <strong>October 2023 Payout</strong>
                                        <span>14 applications • Paid on Nov 5, 2023</span>
                                    </div>
                                    <div className="payout-entry__amount">₹58,000</div>
                                    <span className="status-pill status-pill--success">Paid</span>
                                </div>
                            </div>
                        </Card>
                    </div>
                )}
            </div>
        </div>
    )
}

export default DSA
