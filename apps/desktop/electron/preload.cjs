// Ponte entre a tela e o processo principal. Expõe só três funções, nada do Node.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('atende', {
  plataforma: process.platform,
  chamar: (metodo, argumento) => ipcRenderer.invoke('atende:chamar', metodo, argumento),
  enderecos: () => ipcRenderer.invoke('atende:enderecos'),
  salvarEnderecos: (novos) => ipcRenderer.invoke('atende:salvar-enderecos', novos),
});
