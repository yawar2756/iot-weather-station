    async function updateStatus() {
      const badge = document.getElementById('device-status-badge');
      try {
        const response = await fetch('/api/latest');
        const data = await response.json();

        if (data.device_status === 'Online') {
          badge.className = 'badge badge-success';
          badge.innerHTML = '<span class="badge-dot pulse"></span> System Operational';
        } else {
          badge.className = 'badge badge-danger';
          badge.innerHTML = '<span class="badge-dot pulse"></span> System Offline';
        }
      } catch (error) {
        badge.className = 'badge badge-warning';
        badge.innerHTML = '<span class="badge-dot pulse"></span> Connection Error';
      }
    }

    updateStatus();
    setInterval(updateStatus, 10000);

    // Service Worker Registration
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/service-worker.js')
          .then((reg) => console.log('[SW] Registered:', reg.scope))
          .catch((err) => console.warn('[SW] Registration failed:', err));
      });
    }
  
