import type { Metadata, Viewport } from "next";
import { Geist, JetBrains_Mono, Newsreader } from "next/font/google";
import "./globals.css";

// Self-hosted at build time by next/font: no render-blocking request to
// fonts.googleapis.com, no FOUT, and a metric-matched fallback so the
// first paint doesn't shift. Variable axes, so 400/500/600/700 all come
// from one file.
const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

// Serif display face. The harness emits specifications, so section titles are
// set like a signed engineering document rather than a product headline — it
// is the one typographic signal that separates this console from every
// monospace dev tool. Newsreader is variable, so no weight list is needed.
const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-newsreader",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SDLC Agent Orchestrator",
  description:
    "Multi-agent SDLC harness — 7 specialist subagents, Docker sandbox, LangSmith tracing",
  applicationName: "SDLC Harness",
  openGraph: {
    title: "SDLC Agent Orchestrator",
    description:
      "Multi-agent SDLC harness — 7 specialist subagents, Docker sandbox, LangSmith tracing",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf7f0" },
    { media: "(prefers-color-scheme: dark)", color: "#0b0e0d" },
  ],
};

// Resolve the theme BEFORE first paint. Without this the server always
// emits class="dark" and ThemeToggle only corrects it in an effect, so
// every light-mode load flashed the dark palette for a frame.
// Mirrors ThemeToggle.getInitialTheme() — keep the two in sync.
const THEME_BOOTSTRAP = `
try {
  var t = localStorage.getItem('theme');
  if (t !== 'light' && t !== 'dark') {
    t = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  if (t === 'dark') document.documentElement.classList.add('dark');
} catch (e) {
  document.documentElement.classList.add('dark');
}`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${geist.variable} ${jetbrains.variable} ${newsreader.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP }} />
      </head>
      <body className="bg-base-950 text-base-200 antialiased font-body paper-grain">
        <a href="#main-content" className="skip-link">
          Skip to conversation
        </a>
        {children}
      </body>
    </html>
  );
}
