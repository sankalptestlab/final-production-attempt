import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card, Input } from '../components/ui'
import './Admin.css'

// Mock data for Admin dashboard
const mockAdminData = {
    stats: {
        total_applications: 1256,
        pending_review: 45,
        approved_today: 12,
        disbursed_today: 8,
        total_volume_cr: 45.6,
        avg_processing_hrs: 4.2
    },
    applications: [
        {
            id: 'APP-2024-001',
            business_name: 'Sharma Textiles',
            gst: '27AABCS1429B1ZB',
            amount: 35,
            status: 'pending_review',
            date: '2024-01-12T10:30:00',
            dsa: 'Rajesh Kumar',
            lender: 'HDFC Bank',
            risk_score: 'low',
            cam_ready: true
        },
        {
            id: 'APP-2024-002',
            business_name: 'Tech Innovators LLP',
            gst: '29AABCT8765A1ZM',
            amount: 50,
            status: 'cam_review',
            date: '2024-01-11T14:20:00',
            dsa: 'Priya Sharma',
            lender: 'ICICI Bank',
            risk_score: 'medium',
            cam_ready: true
        },
        {
            id: 'APP-2024-003',
            business_name: 'Green Foods Pvt Ltd',
            gst: '33AABCG2345H1ZP',
            amount: 25,
            status: 'lender_submitted',
            date: '2024-01-10T09:15:00',
            dsa: 'Direct',
            lender: 'Bajaj Finserv',
            risk_score: 'low',
            cam_ready: true
        },
        {
            id: 'APP-2024-004',
            business_name: 'Metro Auto Parts',
            gst: '27AABCM9876C1ZQ',
            amount: 15,
            status: 'documents_pending',
            date: '2024-01-09T16:45:00',
            dsa: 'Amit Singh',
            lender: null,
            risk_score: 'high',
            cam_ready: false
        },
        {
            id: 'APP-2024-005',
            business_name: 'Sunrise Exports',
            gst: '32AABCS5432D1ZR',
            amount: 75,
            status: 'approved',
            date: '2024-01-08T11:30:00',
            dsa: 'Rajesh Kumar',
            lender: 'HDFC Bank',
            risk_score: 'low',
            cam_ready: true
        }
    ],
    lenders: [
        { id: 'hdfc', name: 'HDFC Bank', active: 156, approved: 120, rate: 0.77, volume: 12.5 },
        { id: 'icici', name: 'ICICI Bank', active: 98, approved: 68, rate: 0.69, volume: 8.2 },
        { id: 'bajaj', name: 'Bajaj Finserv', active: 145, approved: 95, rate: 0.66, volume: 7.8 },
        { id: 'ugro', name: 'UGRO Capital', active: 67, approved: 48, rate: 0.72, volume: 4.3 }
    ],
    alerts: [
        { type: 'warning', message: '5 applications pending for >48 hours', count: 5 },
        { type: 'info', message: 'New SCF anchor onboarded: Tata Motors', count: 1 },
        { type: 'error', message: 'HDFC API timeout - 3 failed submissions', count: 3 }
    ]
}

function AdminStatCard({ icon, label, value, subvalue, variant }) {
    return (
        <Card padding="md" className={`admin-stat ${variant ? `admin-stat--${variant}` : ''}`}>
            <div className="admin-stat__icon">{icon}</div>
            <div className="admin-stat__content">
                <span className="admin-stat__label">{label}</span>
                <strong className="admin-stat__value">{value}</strong>
                {subvalue && <span className="admin-stat__subvalue">{subvalue}</span>}
            </div>
        </Card>
    )
}

function ApplicationQueue({ applications }) {
    const getStatusLabel = (status) => {
        const labels = {
            pending_review: 'Pending Review',
            cam_review: 'CAM Review',
            lender_submitted: 'With Lender',
            documents_pending: 'Docs Pending',
            approved: 'Approved',
            rejected: 'Rejected'
        }
        return labels[status] || status
    }

    const getStatusClass = (status) => {
        const classes = {
            pending_review: 'warning',
            cam_review: 'info',
            lender_submitted: 'info',
            documents_pending: 'error',
            approved: 'success',
            rejected: 'error'
        }
        return classes[status] || 'default'
    }

    return (
        <div className="queue">
            {applications.map(app => (
                <div key={app.id} className="queue-item">
                    <div className="queue-item__main">
                        <div className="queue-item__header">
                            <span className="queue-item__id">{app.id}</span>
                            <span className={`status-pill status-pill--${getStatusClass(app.status)}`}>
                                {getStatusLabel(app.status)}
                            </span>
                        </div>
                        <h4 className="queue-item__business">{app.business_name}</h4>
                        <div className="queue-item__meta">
                            <span>₹{app.amount}L</span>
                            <span>•</span>
                            <span>{app.lender || 'Not assigned'}</span>
                            <span>•</span>
                            <span>DSA: {app.dsa}</span>
                        </div>
                    </div>
                    <div className="queue-item__actions">
                        <span className={`risk-badge risk-badge--${app.risk_score}`}>
                            {app.risk_score} risk
                        </span>
                        <Link to={`/admin/application/${app.id}`}>
                            <Button variant="secondary" size="sm">
                                Review →
                            </Button>
                        </Link>
                    </div>
                </div>
            ))}
        </div>
    )
}

function LenderPanel({ lenders }) {
    return (
        <div className="lender-panel">
            {lenders.map(lender => (
                <div key={lender.id} className="lender-row">
                    <div className="lender-row__info">
                        <strong>{lender.name}</strong>
                        <span>{lender.active} active applications</span>
                    </div>
                    <div className="lender-row__stats">
                        <div className="lender-row__stat">
                            <span>{lender.approved}</span>
                            <label>Approved</label>
                        </div>
                        <div className="lender-row__stat">
                            <span>{(lender.rate * 100).toFixed(0)}%</span>
                            <label>Rate</label>
                        </div>
                        <div className="lender-row__stat">
                            <span>₹{lender.volume}Cr</span>
                            <label>Volume</label>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    )
}

function Admin() {
    const [activeTab, setActiveTab] = useState('queue')
    const [searchQuery, setSearchQuery] = useState('')
    const { stats, applications, lenders, alerts } = mockAdminData

    const filteredApps = applications.filter(app =>
        app.business_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.gst.toLowerCase().includes(searchQuery.toLowerCase())
    )

    return (
        <div className="admin-page">
            {/* Header */}
            <div className="admin-header">
                <div className="container">
                    <div className="admin-header__content">
                        <div>
                            <h1>Admin Dashboard</h1>
                            <p>Operations Control Center</p>
                        </div>
                        <div className="admin-header__actions">
                            <Button variant="secondary" size="md">
                                📊 Reports
                            </Button>
                            <Button variant="primary" size="md">
                                ⚙️ Settings
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="container">
                {/* Alerts */}
                {alerts.length > 0 && (
                    <div className="admin-alerts">
                        {alerts.map((alert, index) => (
                            <div key={index} className={`admin-alert admin-alert--${alert.type}`}>
                                <span className="admin-alert__icon">
                                    {alert.type === 'warning' ? '⚠️' : alert.type === 'error' ? '🔴' : 'ℹ️'}
                                </span>
                                <span className="admin-alert__message">{alert.message}</span>
                                <span className="admin-alert__count">{alert.count}</span>
                            </div>
                        ))}
                    </div>
                )}

                {/* Stats Grid */}
                <div className="admin-stats">
                    <AdminStatCard
                        icon="📋"
                        label="Total Applications"
                        value={stats.total_applications.toLocaleString()}
                        subvalue="All time"
                    />
                    <AdminStatCard
                        icon="⏳"
                        label="Pending Review"
                        value={stats.pending_review}
                        subvalue="Need attention"
                        variant="warning"
                    />
                    <AdminStatCard
                        icon="✅"
                        label="Approved Today"
                        value={stats.approved_today}
                        subvalue="vs 10 yesterday"
                        variant="success"
                    />
                    <AdminStatCard
                        icon="💰"
                        label="Disbursed Today"
                        value={stats.disbursed_today}
                        subvalue={`₹${stats.total_volume_cr}Cr total`}
                    />
                    <AdminStatCard
                        icon="⚡"
                        label="Avg Processing"
                        value={`${stats.avg_processing_hrs}hrs`}
                        subvalue="Target: 4hrs"
                    />
                </div>

                {/* Main Content */}
                <div className="admin-grid">
                    {/* Left Panel - Application Queue */}
                    <div className="admin-main">
                        <Card padding="lg">
                            <div className="admin-section-header">
                                <h2>Application Queue</h2>
                                <div className="admin-search">
                                    <Input
                                        placeholder="Search by ID, business name, or GST..."
                                        value={searchQuery}
                                        onChange={setSearchQuery}
                                        icon="🔍"
                                    />
                                </div>
                            </div>

                            <div className="queue-tabs">
                                <button
                                    className={`queue-tab ${activeTab === 'queue' ? 'queue-tab--active' : ''}`}
                                    onClick={() => setActiveTab('queue')}
                                >
                                    Pending Review ({applications.filter(a => a.status === 'pending_review').length})
                                </button>
                                <button
                                    className={`queue-tab ${activeTab === 'cam' ? 'queue-tab--active' : ''}`}
                                    onClick={() => setActiveTab('cam')}
                                >
                                    CAM Review ({applications.filter(a => a.status === 'cam_review').length})
                                </button>
                                <button
                                    className={`queue-tab ${activeTab === 'all' ? 'queue-tab--active' : ''}`}
                                    onClick={() => setActiveTab('all')}
                                >
                                    All ({applications.length})
                                </button>
                            </div>

                            <ApplicationQueue
                                applications={
                                    activeTab === 'queue'
                                        ? filteredApps.filter(a => a.status === 'pending_review')
                                        : activeTab === 'cam'
                                            ? filteredApps.filter(a => a.status === 'cam_review')
                                            : filteredApps
                                }
                            />
                        </Card>
                    </div>

                    {/* Right Panel - Lenders & Actions */}
                    <div className="admin-sidebar">
                        <Card padding="lg">
                            <h3>Lender Performance</h3>
                            <LenderPanel lenders={lenders} />
                        </Card>

                        <Card padding="lg">
                            <h3>Quick Actions</h3>
                            <div className="admin-actions">
                                <Button variant="secondary" fullWidth size="md">
                                    📥 Bulk Upload Applications
                                </Button>
                                <Button variant="secondary" fullWidth size="md">
                                    📤 Export Report
                                </Button>
                                <Button variant="secondary" fullWidth size="md">
                                    🔄 Sync Lender Status
                                </Button>
                                <Button variant="secondary" fullWidth size="md">
                                    👥 Manage DSAs
                                </Button>
                            </div>
                        </Card>

                        <Card padding="lg" variant="outlined">
                            <h3>SCF Anchors</h3>
                            <div className="anchor-list">
                                <div className="anchor-item">
                                    <span className="anchor-item__name">Tata Motors</span>
                                    <span className="anchor-item__status">Active</span>
                                </div>
                                <div className="anchor-item">
                                    <span className="anchor-item__name">Reliance Retail</span>
                                    <span className="anchor-item__status">Active</span>
                                </div>
                                <div className="anchor-item">
                                    <span className="anchor-item__name">Asian Paints</span>
                                    <span className="anchor-item__status">Pending</span>
                                </div>
                            </div>
                            <Button variant="ghost" fullWidth size="sm">
                                + Add Anchor
                            </Button>
                        </Card>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Admin
