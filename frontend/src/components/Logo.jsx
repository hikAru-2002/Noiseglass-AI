// The Noiseglass lens: chaos outside the glass, ranked signal inside.
export default function Logo({ size = 22 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      className="wordmark-mark"
      aria-label="Noiseglass"
    >
      <g fill="currentColor">
        <circle cx="8" cy="12" r="2.2" opacity="0.35" />
        <circle cx="54" cy="8" r="1.8" opacity="0.3" />
        <circle cx="58" cy="52" r="2.4" opacity="0.35" />
        <circle cx="10" cy="54" r="1.6" opacity="0.3" />
        <circle cx="30" cy="5" r="1.9" opacity="0.4" />
        <circle cx="5" cy="32" r="1.7" opacity="0.3" />
      </g>
      <circle
        cx="32"
        cy="32"
        r="19"
        stroke="currentColor"
        strokeWidth="4"
        fill="none"
      />
      <path d="M24 25 H44" stroke="currentColor" strokeWidth="4.2" strokeLinecap="round" />
      <path d="M24 33 H38" stroke="currentColor" strokeWidth="4.2" strokeLinecap="round" opacity="0.65" />
      <path d="M24 41 H31" stroke="currentColor" strokeWidth="4.2" strokeLinecap="round" opacity="0.35" />
    </svg>
  )
}
