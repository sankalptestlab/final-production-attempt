import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Button, Card, Input } from '../components/ui'
import { submitLoanApplication, verifyGST, verifyPAN } from '../services/api'
import './Apply.css'

// Step components
function StepIndicator({ currentStep, steps }) {
    return (
        <div className="step-indicator">
            {steps.map((step, index) => (
                <div
                    key={index}
                    className={`step-indicator__item ${index <= currentStep ? 'step-indicator__item--active' : ''} ${index < currentStep ? 'step-indicator__item--complete' : ''}`}
                >
                    <div className="step-indicator__circle">
                        {index < currentStep ? '✓' : index + 1}
                    </div>
                    <span className="step-indicator__label">{step}</span>
                </div>
            ))}
        </div>
    )
}

// Step 1: Business Identity
function StepBusinessInfo({ data, setData, onNext }) {
    const [errors, setErrors] = useState({})
    const [verifying, setVerifying] = useState(false)

    const validateGST = (gst) => {
        const pattern = /^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$/
        return pattern.test(gst)
    }

    const validatePAN = (pan) => {
        const pattern = /^[A-Z]{5}\d{4}[A-Z]{1}$/
        return pattern.test(pan)
    }

    const handleVerify = async () => {
        console.log('handleVerify called with data:', data)
        const newErrors = {}

        if (!data.gstNumber || !validateGST(data.gstNumber)) {
            newErrors.gstNumber = 'Please enter a valid 15-digit GST number'
            console.log('GST validation failed:', data.gstNumber)
        }

        if (!data.panNumber || !validatePAN(data.panNumber)) {
            newErrors.panNumber = 'Please enter a valid 10-character PAN'
            console.log('PAN validation failed:', data.panNumber)
        }

        console.log('Validation errors:', newErrors)
        setErrors(newErrors)

        if (Object.keys(newErrors).length === 0) {
            setVerifying(true)
            console.log('Starting verification...')
            try {
                // Verify GST and PAN with backend
                console.log('Calling APIs...')
                const [gstResult, panResult] = await Promise.all([
                    verifyGST(data.gstNumber),
                    verifyPAN(data.panNumber)
                ])
                console.log('GST Result:', gstResult)
                console.log('PAN Result:', panResult)

                // Store verification data
                setData({
                    ...data,
                    gstVerified: gstResult.data,
                    panVerified: panResult.data,
                    businessName: gstResult.data?.legal_name || gstResult.data?.trade_name
                })

                setVerifying(false)
                console.log('Verification successful, moving to next step')
                onNext()
            } catch (error) {
                console.error('Verification error:', error)
                setVerifying(false)
                setErrors({ general: `Verification failed: ${error.message}` })
            }
        }
    }

    return (
        <div className="apply-step">
            <div className="apply-step__header">
                <h2>Let's Identify Your Business</h2>
                <p>We'll fetch your business details securely from government databases.</p>
            </div>

            <div className="apply-step__form">
                <Input
                    label="GST Number"
                    placeholder="e.g., 29AABCU9603R1ZM"
                    value={data.gstNumber || ''}
                    onChange={(val) => setData({ ...data, gstNumber: val })}
                    error={errors.gstNumber}
                    autoFormat="gstin"
                    maxLength={15}
                    required
                    icon="🏢"
                    hint="Your 15-digit GSTIN from your GST registration certificate"
                />

                <Input
                    label="PAN Number"
                    placeholder="e.g., AABCU9603R"
                    value={data.panNumber || ''}
                    onChange={(val) => setData({ ...data, panNumber: val })}
                    error={errors.panNumber}
                    autoFormat="pan"
                    maxLength={10}
                    required
                    icon="📄"
                    hint="Your company's or proprietor's PAN"
                />

                <div className="apply-step__info">
                    <div className="info-box">
                        <span className="info-box__icon">🔒</span>
                        <div>
                            <strong>Your data is secure</strong>
                            <p>We use bank-grade encryption. Your information is never shared without explicit consent.</p>
                        </div>
                    </div>
                </div>

                {errors.general && (
                    <div className="apply-step__error" style={{ color: 'red', padding: '10px', marginBottom: '10px', background: '#fee', borderRadius: '8px' }}>
                        {errors.general}
                    </div>
                )}

                <Button
                    onClick={handleVerify}
                    size="lg"
                    fullWidth
                    loading={verifying}
                >
                    {verifying ? 'Verifying...' : 'Verify & Continue'}
                </Button>
            </div>
        </div>
    )
}

// Step 2: Consent
function StepConsent({ data, setData, onNext, onBack }) {
    const [errors, setErrors] = useState({})

    const consents = [
        {
            id: 'creditBureau',
            title: 'Credit Bureau Check',
            description: 'Allow us to check your credit report from CIBIL/Experian. This is required by RBI to assess loan eligibility.',
            required: true
        },
        {
            id: 'dataSharing',
            title: 'Data Sharing with Lenders',
            description: 'Allow us to share your business profile with our partner lenders to get you the best offers.',
            required: true
        },
        {
            id: 'communication',
            title: 'Communication Preferences',
            description: 'Receive updates about your application via WhatsApp, SMS, and Email.',
            required: false
        }
    ]

    const handleContinue = () => {
        const newErrors = {}

        consents.forEach(consent => {
            if (consent.required && !data.consents?.[consent.id]) {
                newErrors[consent.id] = 'This consent is required to proceed'
            }
        })

        setErrors(newErrors)

        if (Object.keys(newErrors).length === 0) {
            onNext()
        }
    }

    const toggleConsent = (id) => {
        setData({
            ...data,
            consents: {
                ...data.consents,
                [id]: !data.consents?.[id]
            }
        })
    }

    return (
        <div className="apply-step">
            <div className="apply-step__header">
                <h2>Consent & Permissions</h2>
                <p>We need your permission to access certain information. This is required by RBI regulations.</p>
            </div>

            <div className="apply-step__form">
                {consents.map(consent => (
                    <div
                        key={consent.id}
                        className={`consent-item ${data.consents?.[consent.id] ? 'consent-item--checked' : ''} ${errors[consent.id] ? 'consent-item--error' : ''}`}
                        onClick={() => toggleConsent(consent.id)}
                    >
                        <div className={`consent-item__checkbox ${data.consents?.[consent.id] ? 'consent-item__checkbox--checked' : ''}`}>
                            {data.consents?.[consent.id] && '✓'}
                        </div>
                        <div className="consent-item__content">
                            <strong className="consent-item__title">
                                {consent.title}
                                {consent.required && <span className="consent-item__required">Required</span>}
                            </strong>
                            <p className="consent-item__description">{consent.description}</p>
                            {errors[consent.id] && (
                                <span className="consent-item__error">{errors[consent.id]}</span>
                            )}
                        </div>
                    </div>
                ))}

                <div className="apply-step__actions">
                    <Button variant="secondary" onClick={onBack} size="lg">
                        ← Back
                    </Button>
                    <Button onClick={handleContinue} size="lg">
                        Continue →
                    </Button>
                </div>
            </div>
        </div>
    )
}

// Step 3: Loan Details
function StepLoanDetails({ data, setData, onNext, onBack }) {
    const [errors, setErrors] = useState({})

    const purposes = [
        { id: 'working_capital', label: 'Working Capital', icon: '💰' },
        { id: 'equipment', label: 'Equipment Purchase', icon: '🏭' },
        { id: 'expansion', label: 'Business Expansion', icon: '📈' },
        { id: 'inventory', label: 'Inventory Purchase', icon: '📦' },
        { id: 'other', label: 'Other', icon: '📋' }
    ]

    const priorities = [
        { id: 'low_interest', label: 'Lowest Interest Rate', icon: '📉' },
        { id: 'quick_disbursement', label: 'Quick Disbursement', icon: '⚡' },
        { id: 'high_amount', label: 'Maximum Amount', icon: '💎' },
        { id: 'low_emi', label: 'Low EMI', icon: '📊' }
    ]

    const handleContinue = () => {
        const newErrors = {}

        if (!data.loanAmount || data.loanAmount < 1) {
            newErrors.loanAmount = 'Please enter the loan amount needed'
        }

        if (!data.loanPurpose) {
            newErrors.loanPurpose = 'Please select a loan purpose'
        }

        setErrors(newErrors)

        if (Object.keys(newErrors).length === 0) {
            onNext()
        }
    }

    return (
        <div className="apply-step">
            <div className="apply-step__header">
                <h2>Loan Requirements</h2>
                <p>Tell us about your funding needs so we can find the best match.</p>
            </div>

            <div className="apply-step__form">
                <Input
                    label="Loan Amount Needed"
                    type="number"
                    placeholder="e.g., 50"
                    value={data.loanAmount || ''}
                    onChange={(val) => setData({ ...data, loanAmount: parseFloat(val) || '' })}
                    error={errors.loanAmount}
                    suffix="Lakhs"
                    icon="₹"
                    required
                />

                <div className="form-group">
                    <label className="form-label">Purpose of Loan <span className="required">*</span></label>
                    <div className="option-grid">
                        {purposes.map(purpose => (
                            <div
                                key={purpose.id}
                                className={`option-card ${data.loanPurpose === purpose.id ? 'option-card--selected' : ''}`}
                                onClick={() => setData({ ...data, loanPurpose: purpose.id })}
                            >
                                <span className="option-card__icon">{purpose.icon}</span>
                                <span className="option-card__label">{purpose.label}</span>
                            </div>
                        ))}
                    </div>
                    {errors.loanPurpose && <span className="form-error">{errors.loanPurpose}</span>}
                </div>

                <div className="form-group">
                    <label className="form-label">What's most important to you?</label>
                    <div className="option-grid option-grid--2">
                        {priorities.map(priority => (
                            <div
                                key={priority.id}
                                className={`option-card ${data.priority === priority.id ? 'option-card--selected' : ''}`}
                                onClick={() => setData({ ...data, priority: priority.id })}
                            >
                                <span className="option-card__icon">{priority.icon}</span>
                                <span className="option-card__label">{priority.label}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="form-group">
                    <label className="form-label">Do you have collateral to offer?</label>
                    <div className="radio-group">
                        <label className={`radio-item ${data.hasCollateral === true ? 'radio-item--selected' : ''}`}>
                            <input
                                type="radio"
                                name="collateral"
                                checked={data.hasCollateral === true}
                                onChange={() => setData({ ...data, hasCollateral: true })}
                            />
                            <span>Yes, I have property/assets</span>
                        </label>
                        <label className={`radio-item ${data.hasCollateral === false ? 'radio-item--selected' : ''}`}>
                            <input
                                type="radio"
                                name="collateral"
                                checked={data.hasCollateral === false}
                                onChange={() => setData({ ...data, hasCollateral: false })}
                            />
                            <span>No, I need an unsecured loan</span>
                        </label>
                    </div>
                </div>

                <div className="apply-step__actions">
                    <Button variant="secondary" onClick={onBack} size="lg">
                        ← Back
                    </Button>
                    <Button onClick={handleContinue} size="lg">
                        Check Eligibility →
                    </Button>
                </div>
            </div>
        </div>
    )
}

// Step 4: Processing
function StepProcessing({ data }) {
    const navigate = useNavigate()
    const [progress, setProgress] = useState(0)
    const [status, setStatus] = useState('Fetching GST data...')
    const [error, setError] = useState(null)

    const stages = [
        'Fetching GST data...',
        'Verifying PAN details...',
        'Checking credit bureau...',
        'Analyzing financials...',
        'Matching with lenders...',
        'Generating offers...'
    ]

    useEffect(() => {
        let isCancelled = false

        const processApplication = async () => {
            // Progress animation
            const interval = setInterval(() => {
                setProgress(prev => {
                    const next = prev + 2
                    if (next <= 90) {
                        const stageIndex = Math.floor((next / 100) * stages.length)
                        setStatus(stages[Math.min(stageIndex, stages.length - 1)])
                        return next
                    }
                    return prev
                })
            }, 100)

            try {
                // Call the real API
                const result = await submitLoanApplication(data)

                if (!isCancelled) {
                    clearInterval(interval)
                    setProgress(100)
                    setStatus('Complete!')

                    // Store results and navigate
                    localStorage.setItem('loanApplicationResult', JSON.stringify(result))

                    setTimeout(() => {
                        navigate(`/results/${result.application_id}`, { state: { result } })
                    }, 500)
                }
            } catch (err) {
                if (!isCancelled) {
                    clearInterval(interval)
                    setError(err.message || 'Application processing failed')
                }
            }
        }

        processApplication()

        return () => {
            isCancelled = true
        }
    }, [navigate, data])

    if (error) {
        return (
            <div className="apply-step apply-step--processing">
                <div className="processing processing--error">
                    <div className="processing__animation">
                        <div className="processing__circle processing__circle--error">
                            <span className="processing__icon">!</span>
                        </div>
                    </div>
                    <h2 className="processing__title">Processing Failed</h2>
                    <p className="processing__status processing__status--error">{error}</p>
                    <Button onClick={() => window.location.reload()} variant="primary" size="lg">
                        Try Again
                    </Button>
                </div>
            </div>
        )
    }

    return (
        <div className="apply-step apply-step--processing">
            <div className="processing">
                <div className="processing__animation">
                    <div className="processing__circle">
                        <div className="processing__spinner"></div>
                        <span className="processing__percent">{progress}%</span>
                    </div>
                </div>

                <h2 className="processing__title">Analyzing Your Profile</h2>
                <p className="processing__status">{status}</p>

                <div className="processing__bar">
                    <div
                        className="processing__bar-fill"
                        style={{ width: `${progress}%` }}
                    ></div>
                </div>

                <div className="processing__details">
                    <Card variant="outlined" padding="md">
                        <div className="processing__detail-item">
                            <span>GST Number</span>
                            <strong>{data.gstNumber}</strong>
                        </div>
                        <div className="processing__detail-item">
                            <span>Loan Amount</span>
                            <strong>₹{data.loanAmount} Lakhs</strong>
                        </div>
                        <div className="processing__detail-item">
                            <span>Purpose</span>
                            <strong>{data.loanPurpose?.replace('_', ' ')}</strong>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    )
}

// Main Apply Component
function Apply() {
    const [searchParams] = useSearchParams()
    const [step, setStep] = useState(0)
    const [formData, setFormData] = useState({
        gstNumber: searchParams.get('gst') || '',
        panNumber: '',
        consents: {},
        loanAmount: '',
        loanPurpose: '',
        priority: 'low_interest',
        hasCollateral: null
    })

    const steps = ['Business Info', 'Consent', 'Loan Details', 'Processing']

    const nextStep = () => setStep(prev => Math.min(prev + 1, steps.length - 1))
    const prevStep = () => setStep(prev => Math.max(prev - 1, 0))

    return (
        <div className="apply-page">
            <div className="container">
                <div className="apply-container">
                    {step < 3 && (
                        <StepIndicator currentStep={step} steps={steps.slice(0, 3)} />
                    )}

                    <Card variant="elevated" padding="lg" className="apply-card">
                        {step === 0 && (
                            <StepBusinessInfo
                                data={formData}
                                setData={setFormData}
                                onNext={nextStep}
                            />
                        )}
                        {step === 1 && (
                            <StepConsent
                                data={formData}
                                setData={setFormData}
                                onNext={nextStep}
                                onBack={prevStep}
                            />
                        )}
                        {step === 2 && (
                            <StepLoanDetails
                                data={formData}
                                setData={setFormData}
                                onNext={nextStep}
                                onBack={prevStep}
                            />
                        )}
                        {step === 3 && (
                            <StepProcessing data={formData} />
                        )}
                    </Card>
                </div>
            </div>
        </div>
    )
}

export default Apply
