import RFB from './vendor/novnc/core/rfb.js';
const screen = document.querySelector('#screen');
const loading = document.querySelector('#loading');
const notice = document.querySelector('#notice');
function notify(message) { notice.textContent = message; notice.style.display = 'block'; setTimeout(() => notice.style.display = 'none', 3500); }
try {
  const response = await fetch('/api/status');
  if (!response.ok) throw new Error('Preview server is unavailable.');
  const config = await response.json();
  const wallpaper = document.querySelector('#wallpaper');
  const reset = document.querySelector('#reset');
  for (const item of config.wallpapers) wallpaper.add(new Option(item.label, item.id));
  wallpaper.value = config.wallpaper;
  let selectedWallpaper = config.wallpaper;
  wallpaper.disabled = false;
  const rfb = new RFB(screen, `ws://127.0.0.1:${config.websocketPort}`, {shared: true});
  rfb.scaleViewport = true; rfb.resizeSession = false; rfb.background = '#30344f';
  rfb.qualityLevel = 7; rfb.compressionLevel = 2;
  rfb.addEventListener('connect', () => { loading.classList.add('hidden'); rfb.focus(); });
  rfb.addEventListener('disconnect', () => { loading.classList.remove('hidden'); loading.querySelector('small').textContent = 'Preview disconnected. Reload to reconnect.'; });
  wallpaper.onchange = async () => {
    wallpaper.disabled = true; reset.disabled = true;
    try {
      const result = await fetch('/api/wallpaper', {
        method: 'POST', headers: {'X-Preview-Action': '1', 'Content-Type': 'application/json'},
        body: JSON.stringify({wallpaper: wallpaper.value})
      });
      if (!result.ok) throw new Error('Could not change the wallpaper.');
      selectedWallpaper = (await result.json()).wallpaper;
      notify(`${wallpaper.selectedOptions[0].textContent} selected.`);
    } catch (error) { wallpaper.value = selectedWallpaper; notify(error.message); }
    finally { wallpaper.disabled = false; reset.disabled = false; }
    rfb.focus();
  };
  reset.onclick = async () => {
    try { const result = await fetch('/api/reset', {method:'POST', headers:{'X-Preview-Action':'1'}}); notify(result.ok ? 'Theme reset.' : 'Could not reset the preview.'); }
    catch { notify('Preview server is unavailable.'); }
    rfb.focus();
  };
  document.querySelector('#fullscreen').onclick = async () => {
    try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); }
    catch { notify('Full screen is unavailable in this browser.'); }
    rfb.focus();
  };
  window.previewRfb = rfb;
} catch(error) { loading.querySelector('small').textContent = error.message; }
