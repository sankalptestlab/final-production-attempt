import { useState } from 'react'
import './Input.css'

function Input({
    label,
    type = 'text',
    placeholder,
    value,
    onChange,
    error,
    hint,
    icon,
    suffix,
    disabled = false,
    required = false,
    maxLength,
    pattern,
    autoFormat,
    ...props
}) {
    const [focused, setFocused] = useState(false)

    const handleChange = (e) => {
        let newValue = e.target.value

        // Auto-formatting for specific types
        if (autoFormat === 'gstin') {
            newValue = newValue.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 15)
        } else if (autoFormat === 'pan') {
            newValue = newValue.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10)
        } else if (autoFormat === 'amount') {
            newValue = newValue.replace(/[^0-9.]/g, '')
        }

        onChange?.(newValue, e)
    }

    const inputClass = [
        'input-wrapper',
        focused && 'input-wrapper--focused',
        error && 'input-wrapper--error',
        disabled && 'input-wrapper--disabled',
    ].filter(Boolean).join(' ')

    return (
        <div className="input-container">
            {label && (
                <label className="input-label">
                    {label}
                    {required && <span className="input-required">*</span>}
                </label>
            )}

            <div className={inputClass}>
                {icon && <span className="input-icon">{icon}</span>}
                <input
                    type={type}
                    className="input"
                    placeholder={placeholder}
                    value={value}
                    onChange={handleChange}
                    onFocus={() => setFocused(true)}
                    onBlur={() => setFocused(false)}
                    disabled={disabled}
                    maxLength={maxLength}
                    pattern={pattern}
                    {...props}
                />
                {suffix && <span className="input-suffix">{suffix}</span>}
            </div>

            {(error || hint) && (
                <span className={`input-message ${error ? 'input-message--error' : ''}`}>
                    {error || hint}
                </span>
            )}
        </div>
    )
}

export default Input
