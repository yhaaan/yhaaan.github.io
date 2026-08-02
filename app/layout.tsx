import type { Metadata } from "next";
import "./globals.css";

const SITE_TITLE = "렌즈 노트 — 개인 게임 디자인 서재";
const SITE_DESCRIPTION =
  "113개의 게임 디자인 렌즈를 직접 기록하고 번호와 키워드로 검색하는 개인 학습 도구입니다.";

const [repositoryOwner = "", repositoryName = ""] =
  process.env.GITHUB_REPOSITORY?.split("/") ?? [];
const isUserPages =
  repositoryName.toLowerCase() ===
  `${repositoryOwner.toLowerCase()}.github.io`;
const isGitHubPagesBuild =
  process.env.GITHUB_ACTIONS === "true" &&
  repositoryOwner.length > 0 &&
  repositoryName.length > 0;
const githubPagesPath =
  repositoryName && !isUserPages ? `/${repositoryName}` : "";
const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ??
  (isGitHubPagesBuild
    ? `https://${repositoryOwner}.github.io${githubPagesPath}`
    : "http://localhost:3000");

export const metadata: Metadata = {
  metadataBase: new URL(`${siteUrl}/`),
  title: SITE_TITLE,
  description: SITE_DESCRIPTION,
  robots: {
    index: false,
    follow: false,
  },
  icons: {
    icon: `${siteUrl}/favicon.svg`,
  },
  openGraph: {
    type: "website",
    locale: "ko_KR",
    url: siteUrl,
    siteName: "렌즈 노트",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    images: [
      {
        url: `${siteUrl}/og-lens-note.png`,
        width: 1731,
        height: 909,
        alt: "빈 렌즈 카드와 돋보기 일러스트레이션",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    images: [`${siteUrl}/og-lens-note.png`],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
