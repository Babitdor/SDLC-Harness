import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // No rewrites needed — frontend calls backend directly at localhost:8000
  // CORS is enabled on the backend (app.py).

  // Standalone output for Docker — produces a self-contained server.js
  // in .next/standalone that bundles all required node_modules.
  output: "standalone",
};

export default nextConfig;