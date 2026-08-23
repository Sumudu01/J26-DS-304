import React from 'react'

function Logo({ className = "h-10 w-auto", light = false }) {
  const color = light ? "#ffffff" : "#002855";
  const contrastColor = light ? "#002855" : "#ffffff";

  return (
    <svg 
      viewBox="0 0 540 100" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* "EMPL" Text */}
      <text 
        x="15" 
        y="72" 
        fontFamily="'Inter', sans-serif" 
        fontWeight="800" 
        fontSize="62" 
        letterSpacing="-1.5" 
        fill={color}
      >
        EMPL
      </text>

      {/* Compass Rose (replaces the 'O') */}
      <g id="compass-rose">
        {/* Outer Ring */}
        <circle 
          cx="210" 
          cy="50" 
          r="32" 
          stroke={color} 
          strokeWidth="2.5" 
          fill="none" 
        />
        
        {/* Inner Ticks or Small Ticks */}
        <circle 
          cx="210" 
          cy="50" 
          r="26" 
          stroke={color} 
          strokeWidth="0.5" 
          strokeDasharray="2 2"
          fill="none" 
        />

        {/* Small letter N at the top */}
        <text 
          x="210" 
          y="10" 
          fontFamily="'Inter', sans-serif" 
          fontWeight="900" 
          fontSize="13" 
          textAnchor="middle" 
          fill={color}
        >
          N
        </text>

        {/* Primary Pointer - NORTH */}
        <polygon points="210,50 210,14 203,50" fill={contrastColor} stroke={color} strokeWidth="1.5" />
        <polygon points="210,50 210,14 217,50" fill={color} />

        {/* Primary Pointer - SOUTH */}
        <polygon points="210,50 210,86 203,50" fill={color} />
        <polygon points="210,50 210,86 217,50" fill={contrastColor} stroke={color} strokeWidth="1.5" />

        {/* Primary Pointer - EAST */}
        <polygon points="210,50 246,50 210,43" fill={color} />
        <polygon points="210,50 246,50 210,57" fill={contrastColor} stroke={color} strokeWidth="1.5" />

        {/* Primary Pointer - WEST */}
        <polygon points="210,50 174,50 210,43" fill={contrastColor} stroke={color} strokeWidth="1.5" />
        <polygon points="210,50 174,50 210,57" fill={color} />

        {/* Secondary Pointers (Diagonal) */}
        {/* NE */}
        <polygon points="210,50 234,26 224,36" fill={color} />
        <polygon points="210,50 234,26 235,39" fill={contrastColor} stroke={color} strokeWidth="1" />

        {/* NW */}
        <polygon points="210,50 186,26 185,39" fill={color} />
        <polygon points="210,50 186,26 196,36" fill={contrastColor} stroke={color} strokeWidth="1" />

        {/* SE */}
        <polygon points="210,50 234,74 235,61" fill={color} />
        <polygon points="210,50 234,74 224,64" fill={contrastColor} stroke={color} strokeWidth="1" />

        {/* SW */}
        <polygon points="210,50 186,74 196,64" fill={color} />
        <polygon points="210,50 186,74 185,61" fill={contrastColor} stroke={color} strokeWidth="1" />

        {/* Center Pivot Point */}
        <circle cx="210" cy="50" r="3.5" fill={contrastColor} stroke={color} strokeWidth="1.5" />
      </g>

      {/* "RERALK" Text */}
      <text 
        x="256" 
        y="72" 
        fontFamily="'Inter', sans-serif" 
        fontWeight="800" 
        fontSize="62" 
        letterSpacing="-1.5" 
        fill={color}
      >
        RERALK
      </text>
    </svg>
  )
}

export default Logo
