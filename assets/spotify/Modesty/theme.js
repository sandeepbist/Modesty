/* Read only our small local palette. No network service or playback reload. */
(() => {
  if (window.__modestyPalette) return;
  window.__modestyPalette = true;
  const style = document.createElement('style');
  style.id = 'modesty-live-palette';
  // Spotify appends its base styles to <head> after theme.js executes.
  // Keep the live sheet last in document order so it wins in both modes.
  document.body.append(style);
  let previous = '', pending = false, timer;
  async function refresh() {
    if (document.hidden || pending) return;
    pending = true;
    try {
      const response = await fetch('/modesty-colors.css', { cache: 'no-store' });
      if (!response.ok) return;
      const css = await response.text();
      if (css.startsWith('/* Modesty palette */') && css !== previous) {
        style.textContent = css;
        previous = css;
      }
    } catch (_) { /* Keep the last palette if Spotify is being updated. */ }
    finally { pending = false; }
  }
  function resume() {
    clearInterval(timer);
    if (!document.hidden) { refresh(); timer = setInterval(refresh, 10000); }
  }
  document.addEventListener('visibilitychange', resume);
  window.addEventListener('focus', refresh);
  resume();
})();
