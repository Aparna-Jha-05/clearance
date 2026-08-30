// CLEARANCE mark: a "C" left open on the right with a latch bridging the gap —
// the letterform for Clearance, and the gate/latch that is the product.
export function Logo({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none" aria-hidden>
      <defs>
        <linearGradient id="clr-grad" x1="2" y1="2" x2="26" y2="26" gradientUnits="userSpaceOnUse">
          <stop stopColor="#5eb0ff" />
          <stop offset="1" stopColor="#c792ea" />
        </linearGradient>
      </defs>
      <rect width="28" height="28" rx="7.5" fill="url(#clr-grad)" />
      <path
        d="M19.1 10.1 A6.4 6.4 0 1 1 19.1 17.9"
        stroke="white" strokeWidth="2.6" fill="none" strokeLinecap="round"
      />
      <rect x="17.5" y="12.35" width="4.1" height="3.3" rx="1.15" fill="white" />
    </svg>
  );
}
