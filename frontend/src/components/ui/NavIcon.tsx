"use client";

import { getNavIcon } from "@/lib/nav-icons";

type NavIconProps = {
  name: string;
  size?: number;
};

export default function NavIcon({ name, size = 20 }: NavIconProps) {
  const Icon = getNavIcon(name);
  return <Icon size={size} stroke={1.75} aria-hidden />;
}
