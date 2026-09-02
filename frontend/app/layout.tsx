import { Big_Shoulders_Stencil, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google"

import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { cn } from "@/lib/utils"

const display = Big_Shoulders_Stencil({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["600", "700", "800"],
})

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["400", "500", "600"],
})

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
})

export const metadata = {
  title: "Baobab Freight Assistant",
  description:
    "Citation-grounded assistant for Baobab Freight & Logistics policy and compliance documents.",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn("antialiased", display.variable, sans.variable, mono.variable, "font-sans")}
    >
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  )
}
