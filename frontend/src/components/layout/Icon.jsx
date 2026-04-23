import React from 'react';

const Icon = ({ name, size = 16, className = "", style = {} }) => {
  const common = {
    width: size, height: size, viewBox: "0 0 24 24",
    fill: "none", stroke: "currentColor", strokeWidth: 1.5,
    strokeLinecap: "round", strokeLinejoin: "round",
    className, style,
  };
  const paths = {
    chat:      <><path d="M4 5h16v11H9l-5 4V5Z"/></>,
    bolt:      <><path d="M13 3 4 14h7l-1 7 9-11h-7l1-7Z"/></>,
    chart:     <><path d="M3 20V9M9 20V4M15 20v-8M21 20v-5"/></>,
    user:      <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    users:     <><circle cx="9" cy="8" r="3.5"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20a6 6 0 0 1 12 0M15 20a5 5 0 0 1 8-4"/></>,
    radio:     <><circle cx="12" cy="12" r="2"/><path d="M7.5 7.5a6 6 0 0 0 0 9M16.5 16.5a6 6 0 0 0 0-9M4.5 4.5a10 10 0 0 0 0 15M19.5 19.5a10 10 0 0 0 0-15"/></>,
    grid:      <><rect x="3" y="3" width="8" height="8"/><rect x="13" y="3" width="8" height="8"/><rect x="3" y="13" width="8" height="8"/><rect x="13" y="13" width="8" height="8"/></>,
    trophy:    <><path d="M7 4h10v4a5 5 0 0 1-10 0V4Z"/><path d="M5 5H2v2a3 3 0 0 0 3 3M19 5h3v2a3 3 0 0 1-3 3M10 16h4M9 20h6M12 16v4"/></>,
    medal:     <><circle cx="12" cy="15" r="5"/><path d="M8 3h8l-2 7-2 1-2-1-2-7Z"/></>,
    target:    <><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/></>,
    board:     <><rect x="3" y="4" width="18" height="16" rx="0"/><path d="M3 9h18M9 4v16"/></>,
    send:      <><path d="m4 4 16 8-16 8 4-8-4-8Z"/></>,
    trash:     <><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></>,
    logout:    <><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l-4-4 4-4M6 12h12"/></>,
    thumbUp:   <><path d="M8 10V20H4V10M8 10l4-7a2 2 0 0 1 2 2v4h6a1 1 0 0 1 1 1l-2 9a2 2 0 0 1-2 2H8"/></>,
    thumbDown: <><path d="M16 14V4h4v10M16 14l-4 7a2 2 0 0 1-2-2v-4H4a1 1 0 0 1-1-1l2-9a2 2 0 0 1 2-2h9"/></>,
    menu:      <><path d="M3 6h18M3 12h18M3 18h18"/></>,
    search:    <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    mic:       <><rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></>,
    alert:     <><path d="M12 4 2 20h20L12 4Z"/><path d="M12 10v4M12 17v.5"/></>,
    check:     <><path d="m4 12 5 5 11-11"/></>,
    chevL:     <><path d="m14 6-6 6 6 6"/></>,
    chevR:     <><path d="m10 6 6 6-6 6"/></>,
    chevD:     <><path d="m6 9 6 6 6-6"/></>,
    close:     <><path d="M5 5l14 14M19 5 5 19"/></>,
    clock:     <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    fire:      <><path d="M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4-1 3 1 4 2 4 1-3-3-6 1-10Z"/></>,
    sparkle:   <><path d="M12 3v6M12 15v6M3 12h6M15 12h6M6 6l4 4M14 14l4 4M18 6l-4 4M10 14l-4 4"/></>,
    settings:  <><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.2-1.6l2-1.5-2-3.4-2.3 1a7 7 0 0 0-2.7-1.6L13.5 2h-3L10 4.9A7 7 0 0 0 7.3 6.5l-2.3-1-2 3.4 2 1.5A7 7 0 0 0 5 12c0 .6.1 1.1.2 1.6l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 2.7 1.6l.5 2.9h3l.5-2.9a7 7 0 0 0 2.7-1.6l2.3 1 2-3.4-2-1.5c.1-.5.2-1 .2-1.6Z"/></>,
    plus:      <><path d="M12 5v14M5 12h14"/></>,
    refresh:   <><path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.5 9a9 9 0 0 0-17 3M3.5 15a9 9 0 0 0 17-3"/></>,
  };
  return <svg {...common}>{paths[name] || null}</svg>;
};

export const DLMark = ({ size = 22 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <rect x="2" y="2" width="20" height="20" stroke="var(--amber)" strokeWidth="1.25" transform="rotate(45 12 12)"/>
    <text x="12" y="14.5" textAnchor="middle" fontFamily="Oswald, sans-serif" fontWeight="700" fontSize="8.5" fill="var(--amber)" letterSpacing="-0.5">DL</text>
  </svg>
);

export default Icon;
