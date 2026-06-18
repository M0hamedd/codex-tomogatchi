const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("tomogatchi", {
  getSnapshot: () => ipcRenderer.invoke("tomogatchi:getSnapshot"),
  care: (kind) => ipcRenderer.invoke("tomogatchi:care", kind),
  sync: () => ipcRenderer.invoke("tomogatchi:sync"),
  install: () => ipcRenderer.invoke("tomogatchi:install"),
  doctor: () => ipcRenderer.invoke("tomogatchi:doctor"),
  setMode: (mode) => ipcRenderer.invoke("tomogatchi:setMode", mode),
  resize: (width, height) => ipcRenderer.invoke("tomogatchi:resize", width, height),
  hide: () => ipcRenderer.invoke("tomogatchi:hide"),
  close: () => ipcRenderer.invoke("tomogatchi:close"),
  quit: () => ipcRenderer.invoke("tomogatchi:quit"),
  onSnapshot: (callback) => {
    const listener = (_event, snapshot) => callback(snapshot);
    ipcRenderer.on("tomogatchi:snapshot", listener);
    return () => ipcRenderer.removeListener("tomogatchi:snapshot", listener);
  },
});
