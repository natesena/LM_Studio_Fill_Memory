/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker
  output: "standalone",

  // Configure port for Docker
  env: {
    PORT: 8080,
  },

  // Enable experimental features if needed
  experimental: {
    // Enable if needed for Docker
  },
};

module.exports = nextConfig;
