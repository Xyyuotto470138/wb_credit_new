import config from '../../frontend/vite.config.js'

export default {
  ...config,
  server: {
    host: '127.0.0.1', port: 15124, strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:18024', rewrite: path => path.replace(/^\/api/, '') } },
  },
}
