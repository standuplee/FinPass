import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: process.env.GITHUB_PAGES === "true" ? "export" : "standalone",
  trailingSlash: process.env.GITHUB_PAGES === "true",
  basePath: process.env.GITHUB_PAGES === "true" ? (process.env.NEXT_PUBLIC_BASE_PATH ?? "") : "",
};

export default nextConfig;
