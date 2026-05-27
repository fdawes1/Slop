const { app, BrowserWindow, session } = require('electron');
const path = require('path');

app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler((_wc, permission, callback) => {
    callback(permission === 'media');
  });

  const win = new BrowserWindow({
    width: 900,
    height: 1020,
    minWidth: 580,
    title: 'NOISEWATCH-7',
    backgroundColor: '#050d12',
    autoHideMenuBar: true,
    webPreferences: { contextIsolation: true },
  });

  win.loadFile(path.join(__dirname, 'noisewatch_scifi.html'));
});

app.on('window-all-closed', () => app.quit());
