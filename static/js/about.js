    // Service Worker Registration
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/service-worker.js')
          .then((reg) => console.log('[SW] Registered:', reg.scope))
          .catch((err) => console.warn('[SW] Registration failed:', err));
      });
    }
  
