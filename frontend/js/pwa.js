// CalorieCast Mobile PWA Controller & Installation Manager
let deferredInstallPrompt = null;

// Register Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' })
      .then(reg => {
        console.log('[PWA] Service Worker registered with scope:', reg.scope);
      })
      .catch(err => {
        // Fallback to /static/sw.js if root /sw.js fails
        navigator.serviceWorker.register('/static/sw.js', { scope: '/' })
          .then(r => console.log('[PWA] Service Worker registered via /static/sw.js'))
          .catch(e => console.warn('[PWA] Service Worker registration failed:', e));
      });
  });
}

// Intercept Native Install Prompt
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  renderInstallBanner();
});

window.addEventListener('appinstalled', () => {
  console.log('[PWA] CalorieCast installed successfully!');
  deferredInstallPrompt = null;
  const banner = document.getElementById('pwa-install-banner');
  if (banner) banner.remove();
});

function isRunningStandalone() {
  return (window.matchMedia('(display-mode: standalone)').matches) ||
         (window.navigator.standalone) ||
         document.referrer.includes('android-app://');
}

function renderInstallBanner() {
  if (isRunningStandalone()) return;
  if (document.getElementById('pwa-install-banner')) return;

  const banner = document.createElement('div');
  banner.id = 'pwa-install-banner';
  banner.style.cssText = `
    position: fixed;
    top: 60px;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 1px solid var(--accent);
    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    border-radius: 12px;
    padding: 0.8rem 1.2rem;
    z-index: 1000;
    display: flex;
    align-items: center;
    gap: 1rem;
    max-width: 90%;
    width: 420px;
    animation: slideDown 0.3s ease;
  `;

  banner.innerHTML = `
    <img src="/static/icons/icon-192.png" alt="App Icon" style="width: 40px; height: 40px; border-radius: 8px;">
    <div style="flex: 1;">
      <strong style="color: var(--text-main); font-size: 0.95rem; display: block;">Install CalorieCast</strong>
      <span style="color: var(--text-muted); font-size: 0.75rem;">Fast fullscreen native fitness experience</span>
    </div>
    <div style="display: flex; gap: 0.4rem;">
      <button type="button" class="btn btn-primary btn-sm" onclick="triggerPwaInstall()">Install</button>
      <button type="button" class="btn btn-secondary btn-sm" onclick="dismissPwaBanner()">✕</button>
    </div>
  `;

  document.body.appendChild(banner);
}

async function triggerPwaInstall() {
  if (!deferredInstallPrompt) {
    alert("To install CalorieCast on your mobile device, open browser menu (⋮) and tap 'Add to Home screen' or 'Install App'.");
    return;
  }
  deferredInstallPrompt.prompt();
  const { outcome } = await deferredInstallPrompt.userChoice;
  console.log(`[PWA] User response to install prompt: ${outcome}`);
  deferredInstallPrompt = null;
  dismissPwaBanner();
}

function dismissPwaBanner() {
  const banner = document.getElementById('pwa-install-banner');
  if (banner) banner.remove();
}

// Check on load
document.addEventListener('DOMContentLoaded', () => {
  if (isRunningStandalone()) {
    document.body.classList.add('pwa-standalone');
    console.log('[PWA] Running in standalone native app mode');
  }
});
