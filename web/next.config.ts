import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // scripts/package.sh builds a self-contained server for the release download
  ...(process.env.NEXT_OUTPUT === "standalone" && {
    output: "standalone" as const,
    // no next/image in the app; this keeps sharp (a per-platform native module) out of the release
    images: { unoptimized: true },
  }),
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
