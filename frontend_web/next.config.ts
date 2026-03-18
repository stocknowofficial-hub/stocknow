import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Cloudflare 구동을 위해 표준 Webpack 사용 (crypto: false 제거)
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
