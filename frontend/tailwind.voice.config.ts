import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/components/ui/ai-voice-input.tsx",
    "./src/components/ui/ai-voice-input-demo.tsx",
    "./src/components/workspace/ChatVoiceControl.tsx",
    "./src/app/(workspace)/dev/voice-input/page.tsx",
  ],
  important: ".kp-voice-root",
  darkMode: ["selector", ".dark"],
  theme: {
    extend: {},
  },
  plugins: [],
} satisfies Config;
