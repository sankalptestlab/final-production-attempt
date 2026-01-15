import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Card, Input } from '../components/ui'
import './Landing.css'

function Landing() {
    const [gstNumber, setGstNumber] = useState('')
    const navigate = useNavigate()

    const handleQuickCheck = (e) => {
        e.preventDefault()
        if (gstNumber.length === 15) {
            navigate(`/apply?gst=${gstNumber}`)
        }
    }

    const features = [
        {
            icon: '⚡',
            title: 'Quick Eligibility',
            description: 'Know your loan eligibility in 2 minutes. No paperwork, just your GST number.'
        },
        {
            icon: '🏦',
            title: 'Multiple Lenders',
            description: 'Compare offers from 15+ banks and NBFCs. Find the best rate for your business.'
        },
        {
            icon: '📊',
            title: 'Credit Intelligence',
            description: 'Get insights on how to improve your eligibility and unlock better rates.'
        },
        {
            icon: '📜',
            title: 'Invoice Discounting',
            description: 'Turn your pending invoices into instant cash. Get up to 90% of invoice value.'
        }
    ]

    const stats = [
        { value: '₹500Cr+', label: 'Loans Facilitated' },
        { value: '10,000+', label: 'MSMEs Served' },
        { value: '15+', label: 'Lending Partners' },
        { value: '2 min', label: 'Average Processing' }
    ]

    const testimonials = [
        {
            quote: "मुझे नहीं पता था कि मेरा GST data इतना valuable है। Udyog Saathi ने मुझे 2 दिन में loan दिलवा दिया!",
            author: 'Ramesh Patel',
            business: 'Textile Manufacturer, Surat',
            avatar: '👨‍💼'
        },
        {
            quote: "As a small IT services company, we struggled to get working capital. Invoice discounting changed everything for us.",
            author: 'Priya Sharma',
            business: 'Tech Solutions, Bangalore',
            avatar: '👩‍💻'
        },
        {
            quote: "எங்கள் business-க்கு first time loan கிடைச்சது. Thank you Udyog Saathi!",
            author: 'Murugan K',
            business: 'Auto Parts Dealer, Chennai',
            avatar: '👨‍🔧'
        }
    ]

    return (
        <div className="landing">
            {/* Hero Section */}
            <section className="hero">
                <div className="hero__background">
                    <div className="hero__multilingual">
                        व्यापार • ব্যবসা • வணிகம் • వ్యాపారం • ವ್ಯಾಪಾರ • ビジネス • 商业 • 사업
                    </div>
                </div>

                <div className="container hero__content">
                    <div className="hero__text animate-slideUp">
                        <h1 className="hero__title">
                            Business Loans Made
                            <span className="hero__title-accent"> Simple</span>
                        </h1>
                        <p className="hero__subtitle">
                            Get personalized loan offers from 15+ lenders in just 2 minutes.
                            No paperwork. No branch visits. Just your GST number.
                        </p>

                        <form className="hero__form" onSubmit={handleQuickCheck}>
                            <div className="hero__input-wrapper">
                                <input
                                    type="text"
                                    className="hero__input"
                                    placeholder="Enter your 15-digit GST Number"
                                    value={gstNumber}
                                    onChange={(e) => setGstNumber(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 15))}
                                    maxLength={15}
                                />
                                <Button type="submit" size="lg" disabled={gstNumber.length !== 15}>
                                    Check Eligibility →
                                </Button>
                            </div>
                            <p className="hero__hint">
                                🔒 Your data is encrypted and secure. We never share without consent.
                            </p>
                        </form>
                    </div>

                    <div className="hero__visual animate-fadeIn">
                        <div className="hero__card hero__card--1">
                            <div className="hero__card-icon">✅</div>
                            <div className="hero__card-text">
                                <strong>₹25L Approved</strong>
                                <span>HDFC Bank • 12.5% p.a.</span>
                            </div>
                        </div>
                        <div className="hero__card hero__card--2">
                            <div className="hero__card-icon">📊</div>
                            <div className="hero__card-text">
                                <strong>Credit Score: Excellent</strong>
                                <span>CMR-2 Rating</span>
                            </div>
                        </div>
                        <div className="hero__card hero__card--3">
                            <div className="hero__card-icon">📜</div>
                            <div className="hero__card-text">
                                <strong>Invoice Discounting</strong>
                                <span>₹15L available @ 1.2%/mo</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Stats Section */}
            <section className="stats">
                <div className="container">
                    <div className="stats__grid">
                        {stats.map((stat, index) => (
                            <div key={index} className="stats__item">
                                <div className="stats__value">{stat.value}</div>
                                <div className="stats__label">{stat.label}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="features" id="how-it-works">
                <div className="container">
                    <div className="features__header">
                        <h2 className="features__title">Why MSMEs Choose Us</h2>
                        <p className="features__subtitle">
                            We believe every small business deserves the same financial tools as large corporations.
                        </p>
                    </div>

                    <div className="features__grid">
                        {features.map((feature, index) => (
                            <Card key={index} hover className="feature-card">
                                <div className="feature-card__icon">{feature.icon}</div>
                                <h3 className="feature-card__title">{feature.title}</h3>
                                <p className="feature-card__description">{feature.description}</p>
                            </Card>
                        ))}
                    </div>
                </div>
            </section>

            {/* How It Works */}
            <section className="how-it-works">
                <div className="container">
                    <div className="features__header">
                        <h2 className="features__title">Get Funded in 3 Steps</h2>
                    </div>

                    <div className="steps">
                        <div className="step">
                            <div className="step__number">1</div>
                            <div className="step__content">
                                <h4 className="step__title">Enter GST Number</h4>
                                <p className="step__text">We fetch your business data securely from government databases</p>
                            </div>
                        </div>
                        <div className="step__connector"></div>
                        <div className="step">
                            <div className="step__number">2</div>
                            <div className="step__content">
                                <h4 className="step__title">Get Matched</h4>
                                <p className="step__text">Our AI matches you with the best lenders for your profile</p>
                            </div>
                        </div>
                        <div className="step__connector"></div>
                        <div className="step">
                            <div className="step__number">3</div>
                            <div className="step__content">
                                <h4 className="step__title">Choose & Apply</h4>
                                <p className="step__text">Select your preferred lender and complete the application</p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Testimonials */}
            <section className="testimonials">
                <div className="container">
                    <div className="features__header">
                        <h2 className="features__title">Trusted by MSMEs Across India</h2>
                    </div>

                    <div className="testimonials__grid">
                        {testimonials.map((testimonial, index) => (
                            <Card key={index} variant="elevated" className="testimonial-card">
                                <p className="testimonial-card__quote">"{testimonial.quote}"</p>
                                <div className="testimonial-card__author">
                                    <span className="testimonial-card__avatar">{testimonial.avatar}</span>
                                    <div>
                                        <strong className="testimonial-card__name">{testimonial.author}</strong>
                                        <span className="testimonial-card__business">{testimonial.business}</span>
                                    </div>
                                </div>
                            </Card>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="cta">
                <div className="container">
                    <Card variant="elevated" className="cta__card">
                        <h2 className="cta__title">Ready to Grow Your Business?</h2>
                        <p className="cta__text">Check your eligibility now. It takes only 2 minutes.</p>
                        <Link to="/apply">
                            <Button size="lg" variant="accent">
                                Get Started Free →
                            </Button>
                        </Link>
                    </Card>
                </div>
            </section>
        </div>
    )
}

export default Landing
