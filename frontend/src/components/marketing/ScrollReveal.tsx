"use client";
import * as React from "react";
import { motion, useInView } from "motion/react";

type Props = {
  children: React.ReactNode;
  delay?: number;
  y?: number;
  style?: React.CSSProperties;
};

export function ScrollReveal({ children, delay = 0, y = 32, style }: Props) {
  const ref = React.useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-72px 0px" });

  return (
    <motion.div
      ref={ref}
      style={style}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.65, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
