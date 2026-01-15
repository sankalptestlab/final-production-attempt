import './Card.css'

function Card({
    children,
    variant = 'default',
    padding = 'md',
    hover = false,
    className = '',
    ...props
}) {
    const cardClass = [
        'card',
        `card--${variant}`,
        `card--padding-${padding}`,
        hover && 'card--hover',
        className,
    ].filter(Boolean).join(' ')

    return (
        <div className={cardClass} {...props}>
            {children}
        </div>
    )
}

export default Card
