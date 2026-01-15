import { Link, useLocation } from 'react-router-dom'
import './Header.css'

function Header() {
    const location = useLocation()
    const isHome = location.pathname === '/'

    return (
        <header className={`header ${isHome ? 'header--transparent' : ''}`}>
            <div className="container">
                <nav className="header__nav">
                    <Link to="/" className="header__logo">
                        <span className="header__logo-icon">🚀</span>
                        <span className="header__logo-text">Udyog Saathi</span>
                    </Link>

                    <div className="header__links">
                        <Link to="/apply" className="header__link">Apply Now</Link>
                        <a href="#how-it-works" className="header__link">How It Works</a>
                        <a href="#products" className="header__link">Products</a>
                    </div>

                    <div className="header__actions">
                        <Link to="/track/demo" className="header__btn header__btn--ghost">
                            Track Application
                        </Link>
                        <Link to="/apply" className="header__btn header__btn--primary">
                            Get Started
                        </Link>
                    </div>
                </nav>
            </div>
        </header>
    )
}

export default Header
