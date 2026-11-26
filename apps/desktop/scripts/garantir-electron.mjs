// O npm recente não roda scripts de instalação de dependências sem aprovação, e é num deles
// que o Electron baixa o próprio executável. Este passo baixa quando ainda não existe.
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

const pasta = path.dirname(createRequire(import.meta.url).resolve('electron/package.json'));
if (!existsSync(path.join(pasta, 'path.txt'))) {
  console.log('Baixando o executável do Electron (só na primeira vez)...');
  const resultado = spawnSync(process.execPath, [path.join(pasta, 'install.js')], { stdio: 'inherit' });
  process.exit(resultado.status ?? 1);
}
