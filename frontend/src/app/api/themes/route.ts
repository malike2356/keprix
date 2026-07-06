import { NextResponse } from "next/server";

const themes = [
  { id: "dark", label: "Dark", mode: "dark" },
  { id: "light", label: "Light", mode: "light" },
  { id: "system", label: "System", mode: "system" },
  { id: "keprix-violet", label: "Keprix Violet", mode: "dark", accent: "#7C3AED" },
  { id: "keprix-cyan", label: "Keprix Cyan", mode: "dark", accent: "#06B6D4" },
];

export async function GET() {
  return NextResponse.json({ themes });
}
