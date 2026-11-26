import { describe, expect, it } from 'vitest';

import { criarServidorDeExemplo, SEM_RESPOSTA } from '../src/api/exemplo';
import { lerDocumento } from '../src/api/real';

describe('servidor de exemplo', () => {
  it('o atendente nunca responde com conteúdo de documento interno', async () => {
    const servidor = criarServidorDeExemplo(0);
    const resposta = await servidor.perguntarAoAtendente('Qual a comissão da equipe?');
    expect(resposta.fontes.map((f) => f.documento)).not.toContain('custos-internos.md');
    const interna = await servidor.buscar({ pergunta: 'comissão da equipe', k: 3, visibilidade: 'interno', modo: 'semantica' });
    expect(interna[0].documento).toBe('custos-internos.md');
    expect((await servidor.perguntarAoAtendente('xyzzy')).texto).toBe(SEM_RESPOSTA);
  });

  it('responde o horário com o trecho certo e a fonte', async () => {
    const resposta = await criarServidorDeExemplo(0).perguntarAoAtendente('Que horas vocês abrem?');
    expect(resposta.texto).toContain('terça a sábado');
    expect(resposta.fontes[0].documento).toBe('faq-salao.md');
  });

  it('enviar, tornar interno e excluir mudam a lista', async () => {
    const servidor = criarServidorDeExemplo(0);
    const antes = (await servidor.listarDocumentos()).length;
    await servidor.enviarDocumento({ nome: 'novo.md', visibilidade: 'publico', conteudo: '## Wi-Fi\n\nA senha é belavista.', arquivo: null });
    const [novo] = await servidor.listarDocumentos();
    expect(novo).toMatchObject({ nome: 'novo.md', trechos: 1, situacao: 'indexado' });
    await servidor.alterarVisibilidade(novo.id, 'interno');
    expect((await servidor.buscar({ pergunta: 'senha wi-fi', k: 3, visibilidade: 'publico', modo: 'palavras' })).map((r) => r.documento)).not.toContain('novo.md');
    await servidor.excluirDocumento(novo.id);
    expect(await servidor.listarDocumentos()).toHaveLength(antes);
  });

  it('os números da avaliação saem das perguntas', async () => {
    const { execucoes, perguntas, k } = await criarServidorDeExemplo(0).avaliacao();
    const ultima = execucoes.at(-1)!;
    expect(ultima.perguntas).toBe(perguntas.length);
    expect(ultima.acertos).toBe(perguntas.filter((p) => p.posicao !== null && p.posicao <= k).length);
  });
});

describe('lerDocumento', () => {
  it('descarta o que vem fora do contrato e assume indexado no servidor de hoje', () => {
    expect(lerDocumento({ id: '1', nome: 'a.md', visibilidade: 'secreto' })).toBeNull();
    expect(lerDocumento('texto')).toBeNull();
    expect(lerDocumento({ id: '1', nome: 'a.pdf', visibilidade: 'interno', trechos: 2, criado_em: '2026-11-22T10:00:00Z' })).toMatchObject({
      situacao: 'indexado', formato: 'pdf', trechos: 2, criadoEm: '2026-11-22T10:00:00Z',
    });
  });
});
