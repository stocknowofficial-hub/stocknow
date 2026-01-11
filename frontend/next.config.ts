import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ['@ionic/react', '@ionic/core', '@stencil/core', 'ionicons'],

};

export default nextConfig;
