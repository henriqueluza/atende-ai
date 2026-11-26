import { describe, expect, it } from 'vitest';

// @ts-expect-error módulo JavaScript do processo principal, sem tipos
import { criarBackend, validarEndereco } from '../electron/backend.mjs';

const ENDERECOS = { coreApi: 'http://localhost:8000', mcp: 'http://localhost:8001', agente: 'http://localhost:8002' };
const ID = '00000000-0000-4000-8000-000000000001';

function redeFalsa(status: number, corpo: unknown) {
  const chamadas: { url: string; metodo: string; corpo?: string }[] = [];
  const buscar = async (url: URL, opcoes: RequestInit) => {
    chamadas.push({ url: String(url), metodo: opcoes.method ?? 'GET', corpo: opcoes.body as string });
    return new Response(status === 204 ? null : JSON.stringify(corpo), { status });
  };
  return { chamadas, backend: criarBackend(ENDERECOS, buscar) };
}

describe('validarEndereco', () => {
  it('aceita http só para a própria máquina e https para qualquer servidor', () => {
    expect(validarEndereco('http://localhost:8000/')).toBe('http://localhost:8000');
    expect(validarEndereco('http://127.0.0.1:8000')).toBe('http://127.0.0.1:8000');
    expect(validarEndereco('https://acervo.exemplo.com.br')).toBe('https://acervo.exemplo.com.br');
    expect(() => validarEndereco('http://192.168.0.10:8000')).toThrow(/https/);
  });

  it('recusa outros protocolos, senha na URL e o que não é endereço', () => {
    for (const ruim of ['file:///etc/passwd', 'javascript:alert(1)', 'http://u:s@localhost', 'localhost', '', 42]) {
      expect(() => validarEndereco(ruim)).toThrow();
    }
  });
});

describe('backend', () => {
  it('não chega à rede quando a entrada do renderer é inválida', async () => {
    const { backend, chamadas } = redeFalsa(200, {});
    await expect(backend.excluirDocumento('../busca')).rejects.toMatchObject({ tipo: 'invalido' });
    await expect(backend.enviarDocumento({ nome: 'a.md', conteudo: 'x', visibilidade: 'todos' })).rejects.toMatchObject({ tipo: 'invalido' });
    await expect(backend.enviarDocumento({ nome: 'a.md', conteudo: 'x'.repeat(1_000_001), visibilidade: 'publico' })).rejects.toMatchObject({ tipo: 'invalido' });
    await expect(backend.buscar({ pergunta: 'oi', k: 99, visibilidade: 'publico' })).rejects.toMatchObject({ tipo: 'invalido' });
    await expect(backend.buscar({ pergunta: 'oi', k: 3, visibilidade: undefined })).rejects.toMatchObject({ tipo: 'invalido' });
    expect(chamadas).toEqual([]);
  });

  it('monta a busca com os parâmetros escapados e sempre com a visibilidade pedida', async () => {
    const { backend, chamadas } = redeFalsa(200, { resultados: [{ trecho: 't', documento: 'd', score: 0.5 }] });
    const resultados = await backend.buscar({ pergunta: 'a&visibilidade=interno', k: 5, visibilidade: 'publico' });
    expect(resultados).toHaveLength(1);
    const url = new URL(chamadas[0].url);
    expect(url.origin + url.pathname).toBe('http://localhost:8000/busca');
    expect(url.searchParams.getAll('visibilidade')).toEqual(['publico']);
    expect(url.searchParams.get('pergunta')).toBe('a&visibilidade=interno');
  });

  it('envia o modo de busca pedido e recusa modo desconhecido', async () => {
    const { backend, chamadas } = redeFalsa(200, { resultados: [] });
    await backend.buscar({ pergunta: 'oi', k: 3, visibilidade: 'publico', modo: 'hibrida' });
    expect(new URL(chamadas[0].url).searchParams.get('modo')).toBe('hibrida');
    await expect(backend.buscar({ pergunta: 'oi', k: 3, visibilidade: 'publico', modo: 'magica' })).rejects.toMatchObject({ tipo: 'invalido' });
  });

  it('envia PDF e imagem no corpo, com nome e visibilidade na URL, e barra o que passa do limite', async () => {
    const { backend, chamadas } = redeFalsa(202, { id: ID, situacao: 'na_fila' });
    const bytes = new Uint8Array([0x25, 0x50, 0x44, 0x46]);
    await backend.enviarArquivo({ nome: 'tabela de preços.pdf', visibilidade: 'interno', bytes: bytes.buffer });
    const url = new URL(chamadas[0].url);
    expect(url.pathname).toBe('/documentos/arquivo');
    expect([url.searchParams.get('nome'), url.searchParams.get('visibilidade')]).toEqual(['tabela de preços.pdf', 'interno']);
    expect(chamadas[0].metodo).toBe('POST');
    await expect(backend.enviarArquivo({ nome: 'a.pdf', visibilidade: 'publico', bytes: new Uint8Array(20 * 1024 * 1024 + 1) })).rejects.toMatchObject({ tipo: 'invalido' });
    await expect(backend.enviarArquivo({ nome: 'a.pdf', visibilidade: 'publico', bytes: 'texto' })).rejects.toMatchObject({ tipo: 'invalido' });
    await expect(backend.enviarArquivo({ nome: 'a.pdf', bytes })).rejects.toMatchObject({ tipo: 'invalido' });
    expect(chamadas).toHaveLength(1);
  });

  it('pergunta ao serviço do atendente, não ao núcleo, e repassa a mensagem de falha dele', async () => {
    const { backend, chamadas } = redeFalsa(200, { texto: 'Das 9h às 19h.', fontes: [], respondeu: true });
    await backend.perguntarAoAtendente({ pergunta: 'Que horas abrem?' });
    expect(chamadas[0]).toMatchObject({ url: 'http://localhost:8002/perguntas', metodo: 'POST' });
    const fora = redeFalsa(503, { detail: 'Chave da Anthropic inválida. Confira ANTHROPIC_API_KEY.' });
    await expect(fora.backend.perguntarAoAtendente({ pergunta: 'oi' })).rejects.toMatchObject({ tipo: 'fora_do_ar', message: 'Chave da Anthropic inválida. Confira ANTHROPIC_API_KEY.' });
  });

  it('separa função ainda não oferecida, recusa e servidor fora do ar', async () => {
    await expect(redeFalsa(404, { detail: 'Not Found' }).backend.avaliacao()).rejects.toMatchObject({ tipo: 'nao_disponivel' });
    await expect(redeFalsa(404, { detail: 'Documento não encontrado.' }).backend.excluirDocumento(ID)).rejects.toMatchObject({ tipo: 'recusado', message: 'Documento não encontrado.' });
    await expect(
      redeFalsa(422, { detail: 'O documento não tem texto para indexar.' }).backend.enviarDocumento({ nome: 'a.md', conteudo: ' ', visibilidade: 'publico' }),
    ).rejects.toMatchObject({ tipo: 'recusado', message: 'O documento não tem texto para indexar.' });
    await expect(redeFalsa(503, {}).backend.listarDocumentos()).rejects.toMatchObject({ tipo: 'fora_do_ar' });
    const semRede = criarBackend(ENDERECOS, async () => { throw new TypeError('fetch failed'); });
    await expect(semRede.listarDocumentos()).rejects.toMatchObject({ tipo: 'fora_do_ar' });
    expect(await semRede.saude()).toEqual({ coreApi: 'fora_do_ar', mcp: 'fora_do_ar', agente: 'fora_do_ar' });
  });

  it('exclui pelo id e devolve a lista do servidor', async () => {
    const exclusao = redeFalsa(204, null);
    await exclusao.backend.excluirDocumento(ID);
    expect(exclusao.chamadas[0]).toMatchObject({ url: `http://localhost:8000/documentos/${ID}`, metodo: 'DELETE' });
    const lista = redeFalsa(200, { documentos: [{ id: ID }] });
    expect(await lista.backend.listarDocumentos()).toEqual([{ id: ID }]);
  });
});
