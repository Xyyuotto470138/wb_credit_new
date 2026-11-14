// Serves the built front end and proxies /api to the local back end. Host and ports come from the environment.
import config from '../../frontend/vite.config.js'

const host = process.env.DEMO_HOST || '127.0.0.1'
const port = Number(process.env.DEMO_PORT || 15224)
const proxy = { '/api': { target: `http://127.0.0.1:${process.env.DEMO_API_PORT || 18124}`, rewrite: path => path.replace(/^\/api/, '') } }
export default {
  ...config,
  server: { ...config.server, host, port, strictPort: true, proxy },
  preview: { host, port, strictPort: true, proxy, allowedHosts: true },
}
