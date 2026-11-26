import react from '@vitejs/plugin-react';
import { defineConfig, type Plugin } from 'vite';

// A página empacotada carrega com uma política de conteúdo fechada (ver index.html).
// Em desenvolvimento o Vite precisa de script inline e de websocket para recarregar a tela.
const CSP_DEV =
  "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; " +
  "font-src 'self'; img-src 'self' data:; connect-src 'self' ws://localhost:*; base-uri 'none'; form-action 'none'";

function cspDeDesenvolvimento(): Plugin {
  return {
    name: 'csp-de-desenvolvimento',
    apply: 'serve',
    transformIndexHtml: (html) =>
      html.replace(/(http-equiv="Content-Security-Policy"\s+content=")[^"]*/, `$1${CSP_DEV}`),
  };
}

export default defineConfig({
  base: './', // caminhos relativos: a página empacotada é aberta do disco
  plugins: [react(), cspDeDesenvolvimento()],
  server: { host: 'localhost', port: 5173, strictPort: false },
  build: { outDir: 'dist', sourcemap: false },
});
