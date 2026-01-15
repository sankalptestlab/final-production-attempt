import { Link } from 'react-router-dom'
import './Footer.css'

function Footer() {
    return (
        <footer className="footer">
            <div className="container">
                <div className="footer__grid">
                    <div className="footer__brand">
                        <Link to="/" className="footer__logo">
                            <span className="footer__logo-icon">🚀</span>
                            <span className="footer__logo-text">Udyog Saathi</span>
                        </Link>
                        <p className="footer__tagline">
                            Empowering MSMEs with accessible business financing
                        </p>
                        <div className="footer__badges">
                            <span className="footer__badge">🔒 256-bit SSL</span>
                            <span className="footer__badge">🏛️ RBI Compliant</span>
                        </div>
                    </div>

                    <div className="footer__column">
                        <h4 className="footer__heading">Products</h4>
                        <ul className="footer__list">
                            <li><a href="#" className="footer__link">Business Loans</a></li>
                            <li><a href="#" className="footer__link">Invoice Discounting</a></li>
                            <li><a href="#" className="footer__link">Working Capital</a></li>
                            <li><a href="#" className="footer__link">Equipment Finance</a></li>
                        </ul>
                    </div>

                    <div className="footer__column">
                        <h4 className="footer__heading">Company</h4>
                        <ul className="footer__list">
                            <li><a href="#" className="footer__link">About Us</a></li>
                            <li><a href="#" className="footer__link">Our Partners</a></li>
                            <li><a href="#" className="footer__link">Careers</a></li>
                            <li><a href="#" className="footer__link">Contact</a></li>
                        </ul>
                    </div>

                    <div className="footer__column">
                        <h4 className="footer__heading">Legal</h4>
                        <ul className="footer__list">
                            <li><a href="#" className="footer__link">Privacy Policy</a></li>
                            <li><a href="#" className="footer__link">Terms of Service</a></li>
                            <li><a href="#" className="footer__link">Grievance Redressal</a></li>
                            <li><a href="#" className="footer__link">Fair Practices Code</a></li>
                        </ul>
                    </div>
                </div>

                <div className="footer__bottom">
                    <p className="footer__copyright">
                        © 2024 Udyog Saathi. All rights reserved.
                    </p>
                    <p className="footer__disclaimer">
                        We are a loan marketplace and do not provide loans directly. All loans are subject to lender approval.
                    </p>
                </div>
            </div>
        </footer>
    )
}

export default Footer
