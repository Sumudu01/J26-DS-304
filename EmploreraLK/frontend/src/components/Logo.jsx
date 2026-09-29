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
      {/* "EMPL" Text - Anchored to the right to maintain exact symmetrical clearance with the compass */}
      <text 
        x="204" 
        y="66" 
        textAnchor="end"
        fontFamily="'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        fontWeight="800" 
        fontSize="54" 
        letterSpacing="-1" 
        fill={color}
      >
        EMPL
      </text>

      {/* Compass Rose (acting as the 'O', vertically and horizontally centered with the letterforms) */}
      <g id="compass-rose" transform="translate(235, 47)">
        {/* Outer Ring - proportional to cap-height */}
        <circle 
          cx="0" 
          cy="0" 
          r="22" 
          stroke={color} 
          strokeWidth="2.2" 
          fill="none" 
        />
        
        {/* Inner Ticks or Small Ticks */}
        <circle 
          cx="0" 
          cy="0" 
          r="17.5" 
          stroke={color} 
          strokeWidth="0.6" 
          strokeDasharray="1.5 1.5" 
          fill="none" 
        />

        {/* Small letter N at the top */}
        <text 
          x="0" 
          y="-25" 
          fontFamily="'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
          fontWeight="900" 
          fontSize="9.5" 
          textAnchor="middle" 
          fill={color}
        >
          N
        </text>

        {/* Primary Pointer - NORTH */}
        <polygon points="0,0 0,-22.5 -4.5,0" fill={contrastColor} stroke={color} strokeWidth="1.2" />
        <polygon points="0,0 0,-22.5 4.5,0" fill={color} />

        {/* Primary Pointer - SOUTH */}
        <polygon points="0,0 0,22.5 -4.5,0" fill={color} />
        <polygon points="0,0 0,22.5 4.5,0" fill={contrastColor} stroke={color} strokeWidth="1.2" />

        {/* Primary Pointer - EAST */}
        <polygon points="0,0 22.5,0 0,-4.5" fill={color} />
        <polygon points="0,0 22.5,0 0,4.5" fill={contrastColor} stroke={color} strokeWidth="1.2" />

        {/* Primary Pointer - WEST */}
        <polygon points="0,0 -22.5,0 0,-4.5" fill={contrastColor} stroke={color} strokeWidth="1.2" />
        <polygon points="0,0 -22.5,0 0,4.5" fill={color} />

        {/* Secondary Pointers (Diagonal) */}
        {/* NE */}
        <polygon points="0,0 15,-15 8.5,-8.5" fill={color} />
        <polygon points="0,0 15,-15 15.5,-6.5" fill={contrastColor} stroke={color} strokeWidth="0.8" />

        {/* NW */}
        <polygon points="0,0 -15,-15 -15.5,-6.5" fill={color} />
        <polygon points="0,0 -15,-15 -8.5,-8.5" fill={contrastColor} stroke={color} strokeWidth="0.8" />

        {/* SE */}
        <polygon points="0,0 15,15 15.5,6.5" fill={color} />
        <polygon points="0,0 15,15 8.5,8.5" fill={contrastColor} stroke={color} strokeWidth="0.8" />

        {/* SW */}
        <polygon points="0,0 -15,15 -8.5,8.5" fill={color} />
        <polygon points="0,0 -15,15 -15.5,6.5" fill={contrastColor} stroke={color} strokeWidth="0.8" />

        {/* Center Pivot Point */}
        <circle cx="0" cy="0" r="2.8" fill={contrastColor} stroke={color} strokeWidth="1.2" />
      </g>

      {/* "RERALK" Text - Anchored to the left to maintain exact symmetrical clearance with the compass */}
      <text 
        x="266" 
        y="66" 
        textAnchor="start"
        fontFamily="'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        fontWeight="800" 
        fontSize="54" 
        letterSpacing="-1" 
        fill={color}
      >
        RERALK
      </text>
    </svg>
  );
}

export default Logo;
