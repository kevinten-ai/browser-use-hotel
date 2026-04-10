"use client";

import { useState, useEffect, useRef, useMemo } from "react";

interface BootLine {
  text: string;
  type:
    | "header"
    | "box"
    | "info"
    | "normal"
    | "success"
    | "progress"
    | "waiting";
  delay: number;
}

const PLATFORM_CONFIG: Record<string, { url: string; code: string }> = {
  携程: { url: "ctrip.com", code: "CTRIP" },
  去哪儿: { url: "qunar.com", code: "QUNAR" },
  同程: { url: "ly.com", code: "TONGCHENG" },
};

function getBootSequence(platform: string): BootLine[] {
  const cfg = PLATFORM_CONFIG[platform] || { url: "unknown", code: "AGENT" };
  return [
    {
      text: "╔══════════════════════════════════╗",
      type: "box",
      delay: 0,
    },
    {
      text: "║  BROWSER-USE AGENT  v0.12.2      ║",
      type: "header",
      delay: 80,
    },
    {
      text: `║  Target: ${cfg.code.padEnd(24)}║`,
      type: "header",
      delay: 160,
    },
    {
      text: "╚══════════════════════════════════╝",
      type: "box",
      delay: 240,
    },
    { text: "", type: "normal", delay: 300 },
    {
      text: "[SYS] Loading Chromium headless...",
      type: "normal",
      delay: 500,
    },
    { text: "  ░░░░░░░░░░░░░░░░░░░░  0%", type: "progress", delay: 900 },
    { text: "  ████████░░░░░░░░░░░░ 42%", type: "progress", delay: 1500 },
    { text: "  ████████████████████ OK", type: "progress", delay: 2200 },
    { text: "[SYS] Viewport → 1920×1080", type: "normal", delay: 2600 },
    {
      text: "[NET] Connecting to GLM-4-Plus...",
      type: "normal",
      delay: 3000,
    },
    { text: "[ OK] AI model online", type: "success", delay: 3700 },
    { text: `[NET] → https://${cfg.url}`, type: "info", delay: 4100 },
    {
      text: "[RUN] Browser session starting",
      type: "normal",
      delay: 4500,
    },
    { text: "[>>>] Waiting for worker", type: "waiting", delay: 5200 },
  ];
}

const LINE_COLORS: Record<string, string> = {
  header: "#00ff41",
  box: "#00ff4150",
  success: "#00ff41",
  info: "#41ffff",
  waiting: "#ffaa00",
  progress: "#00ff41bb",
  normal: "#00ff41aa",
};

function BootAnimationInner({ lines }: { lines: BootLine[] }) {
  const [visibleCount, setVisibleCount] = useState(0);
  const [dots, setDots] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const lastProgressIndex = useMemo(() => {
    let idx = -1;
    lines.forEach((l, i) => {
      if (l.type === "progress") idx = i;
    });
    return idx;
  }, [lines]);

  useEffect(() => {
    const timers = lines.map((_, i) =>
      setTimeout(() => setVisibleCount(i + 1), lines[i].delay)
    );
    return () => timers.forEach(clearTimeout);
  }, [lines]);

  useEffect(() => {
    if (visibleCount < lines.length) return;
    const id = setInterval(() => {
      setDots((d) => (d.length >= 3 ? "" : d + "."));
    }, 500);
    return () => clearInterval(id);
  }, [visibleCount, lines.length]);

  useEffect(() => {
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight });
  }, [visibleCount]);

  return (
    <div className="relative w-full h-full bg-[#0a0c0a] overflow-hidden crt-on">
      {/* Scanlines */}
      <div
        className="absolute inset-0 pointer-events-none z-10 opacity-40"
        style={{
          background:
            "repeating-linear-gradient(0deg, transparent 0px, transparent 2px, rgba(0,0,0,0.3) 2px, rgba(0,0,0,0.3) 4px)",
        }}
      />
      {/* Vignette + glow */}
      <div
        className="absolute inset-0 pointer-events-none z-10"
        style={{
          boxShadow:
            "inset 0 0 80px rgba(0,255,65,0.06), inset 0 0 200px rgba(0,0,0,0.5)",
        }}
      />
      {/* Terminal output */}
      <div
        ref={containerRef}
        className="relative z-0 p-3 h-full overflow-y-auto font-[family-name:var(--font-geist-mono)] text-[11px] leading-[1.7] select-none"
        style={{ textShadow: "0 0 6px rgba(0,255,65,0.35)" }}
      >
        {lines.slice(0, visibleCount).map((line, i) => {
          if (line.type === "progress" && i !== lastProgressIndex) {
            return null;
          }
          return (
            <div
              key={i}
              style={{ color: LINE_COLORS[line.type] || LINE_COLORS.normal }}
              className={line.type === "header" ? "font-bold" : ""}
            >
              {line.text}
              {line.type === "waiting" && (
                <span className="inline-block w-8">{dots}</span>
              )}
            </div>
          );
        })}
        {visibleCount > 0 && (
          <span
            className="inline-block w-[7px] h-[13px] ml-0.5 animate-pulse"
            style={{ backgroundColor: "#00ff41" }}
          />
        )}
      </div>
    </div>
  );
}

export default function BootAnimation({ platform }: { platform: string }) {
  const lines = useMemo(() => getBootSequence(platform), [platform]);
  // Remount the inner component whenever platform changes to restart animation
  // without calling setState directly inside an effect.
  return <BootAnimationInner key={platform} lines={lines} />;
}
