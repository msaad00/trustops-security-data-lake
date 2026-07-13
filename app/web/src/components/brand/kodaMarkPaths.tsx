/** Shared otter mark palette — river-otter fur + brand proof badge. */
export const KODA_OTTER = {
  furDark: "#4a3420",
  furMid: "#7a5c3a",
  furLight: "#e2c9a0",
  muzzle: "#f5ead8",
  belly: "#faf3e8",
  ink: "#101623",
  whisker: "#2d2118",
  kBlue: "#3b6ef5",
  proofGreen: "#047857",
} as const;

/** SVG paths for the 32×32 otter (background gradient applied by KodaMark). */
export function KodaOtterGraphic() {
  const g = KODA_OTTER;
  return (
    <>
      {/* Head — cream face, wider than tall (otter, not cat) */}
      <ellipse cx="16" cy="17.2" rx="9.4" ry="8.2" fill={g.furLight} />
      {/* Dorsal cap + side fur */}
      <path
        d="M6.5 14.5c1.2-4.8 5.2-7.8 9.5-7.8s8.3 3 9.5 7.8c-2.1 1.2-4.6 1.8-7.2 1.6-2.6.2-5.1-.4-7.3-1.6z"
        fill={g.furDark}
      />
      <path
        d="M7.2 12.8c2.4-2.2 5.4-3.2 8.8-3.2s6.4 1 8.8 3.2"
        fill="none"
        stroke={g.furMid}
        strokeWidth="0.6"
        strokeLinecap="round"
      />
      {/* Small side ears (low on head) */}
      <ellipse cx="8.6" cy="12.4" rx="1.7" ry="2.1" fill={g.furDark} />
      <ellipse cx="23.4" cy="12.4" rx="1.7" ry="2.1" fill={g.furDark} />
      <ellipse cx="8.6" cy="12.6" rx="0.85" ry="1" fill={g.furMid} />
      <ellipse cx="23.4" cy="12.6" rx="0.85" ry="1" fill={g.furMid} />
      {/* Eyes — ink black, visible at small sizes */}
      <ellipse cx="12.2" cy="16.2" rx="1.65" ry="1.9" fill={g.ink} />
      <ellipse cx="19.8" cy="16.2" rx="1.65" ry="1.9" fill={g.ink} />
      <circle cx="12.55" cy="15.75" r="0.5" fill="#fff" />
      <circle cx="20.15" cy="15.75" r="0.5" fill="#fff" />
      {/* Muzzle patch */}
      <ellipse cx="16" cy="19.8" rx="4.2" ry="3" fill={g.muzzle} />
      {/* Nose — prominent black */}
      <path
        d="M14.1 19.1h3.8c.9 0 1.5.55 1.35 1.15-.2.85-1.35 1.35-2.75 1.35s-2.55-.5-2.75-1.35c-.15-.6.45-1.15 1.35-1.15z"
        fill={g.ink}
      />
      {/* Whiskers */}
      <path
        d="M9.2 18.6h-2.4M9 20.1h-2.7M9.4 21.5h-2.5M22.8 18.6h2.4M23 20.1h2.7M22.6 21.5h2.5"
        stroke={g.whisker}
        strokeWidth="0.65"
        strokeLinecap="round"
      />
      {/* Belly + K monogram */}
      <ellipse cx="16" cy="23.2" rx="5" ry="3.6" fill={g.belly} />
      <path
        d="M12.8 21.4h2.1v2.4l2.9-2.4h2.3l-3.1 2.8 3.2 3.8h-2.3l-2.7-3.2v3.2h-2.1z"
        fill={g.kBlue}
      />
      {/* Proof badge */}
      <circle
        cx="24.6"
        cy="24.8"
        r="5.4"
        fill="#fff"
        stroke={g.furLight}
        strokeWidth="0.5"
      />
      <path
        d="M22.1 24.8l1.5 1.5 3.2-3.2"
        stroke={g.proofGreen}
        strokeWidth="1.7"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  );
}
