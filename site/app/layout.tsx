import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost:3000";
  const protocol = requestHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const metadataBase = new URL(`${protocol}://${host}`);
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  const publicPath = (path: string) => `${basePath}${path}`;

  return {
    metadataBase,
    title: "U.S. Wildfire Smoke Exposure Trend",
    description:
      "How modeled wildfire-smoke exposure has changed across the United States, with long-run burned-area context.",
    icons: {
      icon: publicPath("/favicon.svg"),
      shortcut: publicPath("/favicon.svg"),
    },
    openGraph: {
      title: "U.S. Wildfire Smoke Exposure Trend",
      description:
        "Modeled U.S. wildfire-smoke exposure trends and long-run burned-area context.",
      type: "website",
      images: [{ url: publicPath("/og.png"), width: 1731, height: 909, alt: "U.S. wildfire-smoke exposure metrics and trend charts" }],
    },
    twitter: {
      card: "summary_large_image",
      title: "U.S. Wildfire Smoke Exposure Trend",
      description: "Modeled U.S. wildfire-smoke exposure trends and long-run burned-area context.",
      images: [publicPath("/og.png")],
    },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
