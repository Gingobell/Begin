/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow CopilotKit to proxy requests to the FastAPI backend
  async rewrites() {
    return [];
  },
};

export default nextConfig;
