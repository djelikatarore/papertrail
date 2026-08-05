const RADIUS = 18;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export default function SimilarityRing({ percentage, size = 56 }) {
  const offset = CIRCUMFERENCE * (1 - percentage / 100);

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox="0 0 44 44" className="-rotate-90">
        <circle cx="22" cy="22" r={RADIUS} fill="none" stroke="var(--color-border)" strokeWidth="3.5" />
        <circle
          cx="22"
          cy="22"
          r={RADIUS}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="3.5"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-accent">
        {percentage}%
      </span>
    </div>
  );
}
