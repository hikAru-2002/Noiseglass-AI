import { useNavigate } from 'react-router-dom'
import { useEffect, useRef } from 'react'
import AmbientField from './components/AmbientField.jsx'
import Logo from './components/Logo.jsx'
import './Landing.css'

function useRevealOnScroll() {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add('reveal-visible')
          observer.disconnect()
        }
      },
      { threshold: 0.15 }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])
  return ref
}

function RevealSection({ children, className = '' }) {
  const ref = useRevealOnScroll()
  return (
    <div ref={ref} className={`reveal ${className}`}>
      {children}
    </div>
  )
}

export default function Landing() {
  const navigate = useNavigate()

  function handleCardMove(e) {
    const card = e.currentTarget
    const rect = card.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const rotateX = ((y - rect.height / 2) / rect.height) * -6
    const rotateY = ((x - rect.width / 2) / rect.width) * 6
    card.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`
  }

  function handleCardLeave(e) {
    e.currentTarget.style.transform = 'perspective(800px) rotateX(0deg) rotateY(0deg)'
  }

  return (
    <div className="landing">
      <AmbientField />

      <nav className="landing-nav">
        <div className="landing-wordmark">
          <Logo size={20} />
          <span>Noiseglass</span>
        </div>
        <button className="nav-launch-btn" onClick={() => navigate('/app')}>
          Launch console
        </button>
      </nav>

      <section className="hero">
        <div className="hero-masthead" aria-label="Noiseglass">
          NOISEGLASS
        </div>
        <h1 className="hero-title">
          Cut through the noise.<br />See the real signal.
        </h1>
        <p className="hero-sub">
          Noiseglass clusters any pile of raw feedback into ranked, actionable trends,
          powered by Claude and real deterministic math, not guesswork.
        </p>
        <button className="hero-cta" onClick={() => navigate('/app')}>
          Launch console
        </button>

        <div
          className="hero-card"
          onMouseMove={handleCardMove}
          onMouseLeave={handleCardLeave}
        >
          <div className="hero-card-top">
            <span className="hero-card-severity mono">high</span>
            <span className="hero-card-count mono">19 fragments</span>
          </div>
          <div className="hero-card-title">Integration Auth Error</div>
          <p className="hero-card-text">
            Auth failures holding flat at 5 per week across HubSpot, Slack, Salesforce and Google Workspace.
          </p>
        </div>
      </section>

      <RevealSection className="features">
        <div className="feature">
          <span className="feature-number mono">01</span>
          <h3>Any data, zero integration</h3>
          <p>Drop in a CSV, paste raw text, pull live from GitHub or Zendesk, or point any MCP-capable AI agent at it directly. If it's text, Noiseglass reads it.</p>
        </div>
        <div className="feature">
          <span className="feature-number mono">02</span>
          <h3>Hybrid intelligence</h3>
          <p>Claude reads the messy text. Deterministic Python does the math. Trend numbers you can trust.</p>
        </div>
        <div className="feature">
          <span className="feature-number mono">03</span>
          <h3>Built to persist</h3>
          <p>Every run stored in Postgres. Every migration tracked. Nothing disappears on redeploy.</p>
        </div>
      </RevealSection>

      <RevealSection className="cta-section">
        <h2>Ready to see your signal?</h2>
        <button className="hero-cta" onClick={() => navigate('/app')}>
          Launch console
        </button>
      </RevealSection>
    </div>
  )
}
