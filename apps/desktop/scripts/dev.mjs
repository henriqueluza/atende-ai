// Sobe o Vite e abre o Electron apontando para ele. Uso: npm run dev
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { createServer } from 'vite';

const servidor = await createServer();
await servidor.listen();
const porta = servidor.config.server.port;
const electron = createRequire(import.meta.url)('electron'); // caminho do executável

const janela = spawn(electron, ['.'], {
  stdio: 'inherit',
  env: { ...process.env, ATENDE_DEV_URL: `http://localhost:${porta}/` },
});
janela.on('exit', async (codigo) => {
  await servidor.close();
  process.exit(codigo ?? 0);
});
