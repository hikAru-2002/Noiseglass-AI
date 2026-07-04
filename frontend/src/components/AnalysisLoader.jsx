import { useEffect, useRef, useState } from 'react'

const PHASES = [
  'reading tickets',
  'normalizing issues',
  'clustering by root cause',
  'computing week-over-week trends',
  'writing headlines + actions',
]

const CYCLE_MS = 7000 // one scatter->cluster cycle
const CLUSTER_COUNT = 5

export default function AnalysisLoader({ ticketCount = 0, sourceName = null }) {
  const canvasRef = useRef(null)
  const [phaseIdx, setPhaseIdx] = useState(0)

  useEffect(() => {
    const id = setInterval(
      () => setPhaseIdx((i) => (i + 1) % PHASES.length),
      3200
    )
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1

    let width = 0
    let height = 0
    let raf = 0
    let particles = []
    let centers = []
    const mouse = { x: -9999, y: -9999 }
    let shock = null // { x, y, t }

    function resize() {
      const rect = canvas.getBoundingClientRect()
      width = rect.width
      height = rect.height
      canvas.width = width * dpr
      canvas.height = height * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    function seedCenters() {
      centers = Array.from({ length: CLUSTER_COUNT }, (_, i) => ({
        x: width * (0.16 + 0.68 * (i / (CLUSTER_COUNT - 1))) +
          (Math.random() - 0.5) * width * 0.08,
        y: height * (0.3 + Math.random() * 0.4),
        drift: Math.random() * Math.PI * 2,
      }))
    }

    function seedParticles() {
      const n = Math.min(Math.max(ticketCount, 40), 140)
      particles = Array.from({ length: n }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        cluster: Math.floor(Math.random() * CLUSTER_COUNT),
        size: 1 + Math.random() * 1.6,
      }))
    }

    function step(now) {
      ctx.clearRect(0, 0, width, height)

      // 0 -> 1 within each cycle: how "clustered" we are
      const t = (now % CYCLE_MS) / CYCLE_MS
      // ease in, hold, release: cluster strength curve
      const strength =
        t < 0.55 ? t / 0.55 : t < 0.85 ? 1 : 1 - (t - 0.85) / 0.15

      centers.forEach((c, i) => {
        c.drift += 0.003
        c.cx = c.x + Math.cos(c.drift + i) * 14
        c.cy = c.y + Math.sin(c.drift * 1.3 + i) * 10
      })

      for (const p of particles) {
        const c = centers[p.cluster]

        // pull toward cluster center, scaled by cycle strength
        p.vx += (c.cx - p.x) * 0.0009 * strength
        p.vy += (c.cy - p.y) * 0.0009 * strength

        // gentle brownian noise, stronger when scattered
        p.vx += (Math.random() - 0.5) * 0.06 * (1.2 - strength)
        p.vy += (Math.random() - 0.5) * 0.06 * (1.2 - strength)

        // mouse repulsion
        const mdx = p.x - mouse.x
        const mdy = p.y - mouse.y
        const mdist = Math.hypot(mdx, mdy)
        if (mdist < 70 && mdist > 0.01) {
          const f = ((70 - mdist) / 70) * 0.6
          p.vx += (mdx / mdist) * f
          p.vy += (mdy / mdist) * f
        }

        // click shockwave
        if (shock) {
          const age = (now - shock.t) / 600
          if (age < 1) {
            const r = age * 180
            const sdx = p.x - shock.x
            const sdy = p.y - shock.y
            const sdist = Math.hypot(sdx, sdy)
            if (Math.abs(sdist - r) < 30 && sdist > 0.01) {
              const f = (1 - age) * 1.6
              p.vx += (sdx / sdist) * f
              p.vy += (sdy / sdist) * f
            }
          } else {
            shock = null
          }
        }

        p.vx *= 0.94
        p.vy *= 0.94
        p.x += p.vx
        p.y += p.vy

        // soft wrap at edges
        if (p.x < -10) p.x = width + 10
        if (p.x > width + 10) p.x = -10
        if (p.y < -10) p.y = height + 10
        if (p.y > height + 10) p.y = -10
      }

      // faint connective lines within clusters once mostly formed
      if (strength > 0.6) {
        const lineAlpha = (strength - 0.6) * 0.22
        ctx.lineWidth = 0.5
        for (const p of particles) {
          const c = centers[p.cluster]
          const d = Math.hypot(p.x - c.cx, p.y - c.cy)
          if (d < 46) {
            ctx.strokeStyle = `rgba(255,255,255,${lineAlpha * (1 - d / 46)})`
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(c.cx, c.cy)
            ctx.stroke()
          }
        }
      }

      // particles: brighter as they cluster
      for (const p of particles) {
        const alpha = 0.3 + strength * 0.55
        ctx.fillStyle = `rgba(255,255,255,${alpha})`
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fill()
      }

      raf = requestAnimationFrame(step)
    }

    function onMove(e) {
      const rect = canvas.getBoundingClientRect()
      mouse.x = e.clientX - rect.left
      mouse.y = e.clientY - rect.top
    }
    function onLeave() {
      mouse.x = -9999
      mouse.y = -9999
    }
    function onClick(e) {
      const rect = canvas.getBoundingClientRect()
      shock = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        t: performance.now(),
      }
    }
    function onResize() {
      resize()
      seedCenters()
    }

    resize()
    seedCenters()
    seedParticles()
    raf = requestAnimationFrame(step)

    canvas.addEventListener('mousemove', onMove)
    canvas.addEventListener('mouseleave', onLeave)
    canvas.addEventListener('click', onClick)
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      canvas.removeEventListener('mousemove', onMove)
      canvas.removeEventListener('mouseleave', onLeave)
      canvas.removeEventListener('click', onClick)
      window.removeEventListener('resize', onResize)
    }
  }, [ticketCount])

  return (
    <div className="analysis-loader">
      <canvas ref={canvasRef} className="analysis-loader-canvas" />
      {sourceName && (
        <div className="analysis-loader-source">
          <span className="analysis-loader-source-label mono">analyzing</span>
          <span className="analysis-loader-source-name">{sourceName}</span>
        </div>
      )}
      <div className="analysis-loader-status mono">
        <span className="analysis-loader-phase" key={phaseIdx}>
          {PHASES[phaseIdx]}
        </span>
        <span className="analysis-loader-caret" />
      </div>
      <p className="analysis-loader-hint">
        {ticketCount} tickets{sourceName ? ` from ${sourceName}` : ''} resolving
        into signal. Move your cursor through the noise, click to send a pulse.
      </p>
    </div>
  )
}
