// Processo principal: cria a janela e é o único ponto que fala com a rede.
// A tela roda isolada (sandbox, sem Node) e só alcança o que o preload expõe.

import { app, BrowserWindow, ipcMain, session, shell } from 'electron';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { criarBackend, ENDERECOS_PADRAO, ErroBackend, SERVICOS, validarEndereco } from './backend.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const INDEX = path.join(AQUI, '..', 'dist', 'index.html');

// Só em desenvolvimento, e só para o Vite desta máquina. Um app empacotado ignora a variável.
const URL_DEV = (() => {
  const valor = process.env.ATENDE_DEV_URL;
  if (app.isPackaged || !valor) return null;
  const url = new URL(valor);
  return url.protocol === 'http:' && url.hostname === 'localhost' ? url : null;
})();

const METODOS = new Set([
  'saude',
  'listarDocumentos',
  'enviarDocumento',
  'enviarArquivo',
  'excluirDocumento',
  'alterarVisibilidade',
  'detalharDocumento',
  'buscar',
  'perguntarAoAtendente',
  'avaliacao',
  'rodarAvaliacao',
]);

const arquivoDeConfig = () => path.join(app.getPath('userData'), 'config.json');

async function lerEnderecos() {
  const padrao = {
    coreApi: process.env.CORE_API_URL || ENDERECOS_PADRAO.coreApi,
    mcp: process.env.MCP_SERVER_URL || ENDERECOS_PADRAO.mcp,
    agente: process.env.AGENT_URL || ENDERECOS_PADRAO.agente,
  };
  let salvo = {};
  try {
    salvo = JSON.parse(await readFile(arquivoDeConfig(), 'utf8'));
  } catch {
    salvo = {}; // primeira execução ou arquivo corrompido: volta ao padrão
  }
  const enderecos = {};
  for (const chave of SERVICOS) {
    try {
      enderecos[chave] = validarEndereco(salvo[chave] ?? padrao[chave]);
    } catch {
      enderecos[chave] = ENDERECOS_PADRAO[chave];
    }
  }
  return enderecos;
}

async function salvarEnderecos(novos) {
  const enderecos = Object.fromEntries(SERVICOS.map((chave) => [chave, validarEndereco(novos?.[chave])]));
  await mkdir(path.dirname(arquivoDeConfig()), { recursive: true });
  await writeFile(arquivoDeConfig(), JSON.stringify(enderecos, null, 2), { mode: 0o600 });
  return enderecos;
}

/** A chamada tem que vir da nossa própria página, no quadro principal. */
function vemDaNossaTela(evento) {
  const quadro = evento.senderFrame;
  if (!quadro || quadro.parent) return false;
  try {
    const url = new URL(quadro.url);
    if (URL_DEV) return url.origin === URL_DEV.origin;
    return url.protocol === 'file:' && url.pathname === pathToFileURL(INDEX).pathname;
  } catch {
    return false;
  }
}

function falha(erro) {
  if (erro instanceof ErroBackend) return { ok: false, erro: { tipo: erro.tipo, mensagem: erro.message } };
  console.error('Falha inesperada no processo principal:', erro);
  // O detalhe fica no log. Para a tela vai só uma mensagem genérica.
  return { ok: false, erro: { tipo: 'erro', mensagem: 'Algo deu errado no aplicativo.' } };
}

function registrarIpc(estado) {
  const proteger = (tratador) => async (evento, ...argumentos) => {
    if (!vemDaNossaTela(evento)) return falha(new ErroBackend('invalido', 'Origem não autorizada.'));
    try {
      return { ok: true, dados: await tratador(...argumentos) };
    } catch (erro) {
      return falha(erro);
    }
  };

  ipcMain.handle(
    'atende:chamar',
    proteger((metodo, argumento) => {
      if (typeof metodo !== 'string' || !METODOS.has(metodo)) {
        throw new ErroBackend('invalido', 'Operação desconhecida.');
      }
      return estado.backend[metodo](argumento);
    }),
  );
  ipcMain.handle('atende:enderecos', proteger(() => estado.enderecos));
  ipcMain.handle(
    'atende:salvar-enderecos',
    proteger(async (novos) => {
      estado.enderecos = await salvarEnderecos(novos);
      estado.backend = criarBackend(estado.enderecos);
      return estado.enderecos;
    }),
  );
}

function criarJanela() {
  const janela = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 720,
    minHeight: 560,
    show: false,
    backgroundColor: '#f4f7f7',
    title: 'atende-ai',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    webPreferences: {
      preload: path.join(AQUI, 'preload.cjs'),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      webSecurity: true,
      spellcheck: false,
    },
  });
  janela.once('ready-to-show', () => janela.show());

  // A janela só mostra a nossa tela. Link externo abre no navegador, e só se for https.
  janela.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://')) shell.openExternal(url);
    return { action: 'deny' };
  });
  janela.webContents.on('will-navigate', (evento) => evento.preventDefault());
  janela.webContents.on('will-attach-webview', (evento) => evento.preventDefault());

  if (URL_DEV) janela.loadURL(URL_DEV.href);
  else janela.loadFile(INDEX);
}

app.whenReady().then(async () => {
  // Nenhuma permissão de navegador (câmera, localização, notificação...) é concedida.
  session.defaultSession.setPermissionRequestHandler((_conteudo, _permissao, responder) => responder(false));
  session.defaultSession.setPermissionCheckHandler(() => false);

  const enderecos = await lerEnderecos();
  registrarIpc({ enderecos, backend: criarBackend(enderecos) });
  criarJanela();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) criarJanela();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
