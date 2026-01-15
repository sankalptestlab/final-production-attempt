import './Button.css'

function Button({
    children,
    variant = 'primary',
    size = 'md',
    fullWidth = false,
    disabled = false,
    loading = false,
    icon,
    onClick,
    type = 'button',
    ...props
}) {
    const className = [
        'btn',
        `btn--${variant}`,
        `btn--${size}`,
        fullWidth && 'btn--full',
        loading && 'btn--loading',
        disabled && 'btn--disabled',
    ].filter(Boolean).join(' ')

    return (
        <button
            className={className}
            onClick={onClick}
            disabled={disabled || loading}
            type={type}
            {...props}
        >
            {loading ? (
                <span className="btn__spinner" />
            ) : (
                <>
                    {icon && <span className="btn__icon">{icon}</span>}
                    {children}
                </>
            )}
        </button>
    )
}

export default Button
