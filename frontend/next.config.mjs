/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ["begin.gintarot.com"],
  // Allow CopilotKit to proxy requests to the FastAPI backend
  async rewrites() {
    return [];
  },
};

export default nextConfig;
