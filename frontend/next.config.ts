import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ['@ionic/react', '@ionic/core', '@stencil/core', 'ionicons'],
  // @ts-ignore - Next.js 16 types might not be updated yet
  allowedDevOrigins: ["192.168.0.221:3000", "localhost:3000"],

};

export default nextConfig;
