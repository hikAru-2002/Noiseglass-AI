import { useEffect, useRef } from 'react'

/**
 * Full-screen, non-interactive ambient particle field for the landing page.
 * Slow-drifting dots with faint constellation lines — same visual language
 * as the analysis loader, but purely atmospheric.
 */
export default function AmbientField() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1

    let width = 0
    let height = 0
    let raf = 0
    let particles = []

    function resize() {
      width = window.innerWidth
      height = window.innerHeight
      canvas.width = width * dpr
      canvas.height = height * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    function seed() {
      const n = Math.min(Math.floor((width * height) / 18000), 90)
      particles = Array.from({ length: n }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.18,
        vy: (Math.random() - 0.5) * 0.18,
        size: 0.8 + Math.random() * 1.4,
        phase: Math.random() * Math.PI * 2,
      }))
    }

    function step(now) {
      ctx.clearRect(0, 0, width, height)

      for (const p of particles) {
        p.x += p.vx
        p.y += p.vy

        if (p.x < -12) p.x = width + 12
        if (p.x > width + 12) p.x = -12
        if (p.y < -12) p.y = height + 12
        if (p.y > height + 12) p.y = -12
      }

      // constellation lines between nearby particles
      ctx.lineWidth = 0.5
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i]
          const b = particles[j]
          const dx = a.x - b.x
          const dy = a.y - b.y
          const d2 = dx * dx + dy * dy
          if (d2 < 120 * 120) {
            const d = Math.sqrt(d2)
            ctx.strokeStyle = `rgba(255,255,255,${0.06 * (1 - d / 120)})`
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.stroke()
          }
        }
      }

      // dots with a slow breathing shimmer
      for (const p of particles) {
        const twinkle = 0.18 + 0.14 * Math.sin(now * 0.0006 + p.phase)
        ctx.fillStyle = `rgba(255,255,255,${twinkle})`
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fill()
      }

      raf = requestAnimationFrame(step)
    }

    function onResize() {
      resize()
      seed()
    }

    resize()
    seed()
    raf = requestAnimationFrame(step)
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', onResize)
    }
  }, [])

  return <canvas ref={canvasRef} className="ambient-field" aria-hidden="true" />
}
