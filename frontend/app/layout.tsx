import type { Metadata } from "next";
import { Fraunces, Instrument_Sans, Instrument_Serif, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const instrument = Instrument_Sans({
  subsets: ["latin"],
  variable: "--font-instrument",
});

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-instrument-serif",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-jetbrains",
});

// Fraunces — a soft, characterful "old-style" serif for the storybook voice
// (Sprout's Ghibli-cozy display type). Variable font, normal + italic.
const fraunces = Fraunces({
  subsets: ["latin"],
  style: ["normal", "italic"],
  variable: "--font-fraunces",
});

export const metadata: Metadata = {
  title: "Sprout — a calm home for the videos you'll grow",
  description:
    "Connect YouTube once. Sprout learns what actually converts for you, does the research so you don't, and hands back cited video ideas — a garden you tend, not a dashboard you check. Built on Cognee.",
  icons: {
    icon: [{ url: "/icon.png" }, { url: "/favicon.ico", sizes: "16x16" }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body
        className={`${instrument.variable} ${instrumentSerif.variable} ${jetbrains.variable} ${fraunces.variable} atmosphere antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
