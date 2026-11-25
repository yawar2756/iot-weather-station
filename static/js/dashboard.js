    // ============ CONFIG ============
    const POLL_INTERVAL = 10000;           // Poll /api/latest every 10s
    const CHART_REFRESH_INTERVAL = 300000; // Refresh chart every 5 min
    const TOAST_DURATION = 5000;

    // ============ STATE ============
    let weatherChart = null;
    let chartMode = 'hourly';
    let lastUpdate = null;   // set from the server timestamp, not page-load time
    let lastAlert = null;
    let lastData = {};

    // ============ CHART CONFIG ============
    const chartConfig = {
      type: 'line',
      data: { labels: [], datasets: [{
        label: 'Temperature (°C)',
        data: [],
        borderColor: '#38BDF8',
        backgroundColor: 'rgba(56, 189, 248, 0.1)',
        borderWidth: 3,
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#38BDF8',
        pointBorderWidth: 0
      }]},
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          autoPadding: true,
          padding: { top: 10, right: 20, bottom: 10, left: 10 }
        },
        animation: { duration: 750, easing: 'easeOutQuart' },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0F172A',
            padding: 12,
            titleFont: { size: 14, weight: 'bold' },
            bodyFont: { size: 13 },
            displayColors: false,
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1
          }
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#64748B', font: { size: 11 } } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748B', font: { size: 11 } } }
        }
      }
    };

    // ============ DOM HELPERS ============
    const $ = (id) => document.getElementById(id);
    const setText = (id, text) => { const el = $(id); if (el) el.innerText = text; };
    const setClass = (el, ...classes) => { if (el) el.className = classes.join(' '); };
    const addClass = (el, ...classes) => { if (el) el.classList.add(...classes); };
    const removeClass = (el, ...classes) => { if (el) el.classList.remove(...classes); };

    // ============ TOAST SYSTEM ============
    function showToast(type, title, message) {
      const container = $('toast-container');
      const toast = document.createElement('div');
      toast.className = `toast ${type === 'critical' ? 'toast-danger' : type === 'warning' ? 'toast-warning' : 'toast-info'}`;
      const icons = { critical: 'fa-triangle-exclamation', warning: 'fa-circle-exclamation', info: 'fa-circle-info' };
      toast.innerHTML = `
        <i class="fas ${icons[type]} toast-icon"></i>
        <div class="toast-content">
          <div class="toast-title">${title}</div>
          <div class="toast-message">${message}</div>
        </div>
      `;
      container.appendChild(toast);
      setTimeout(() => removeToast(toast), TOAST_DURATION);
    }

    function removeToast(toast) {
      toast.classList.add('removing');
      setTimeout(() => toast.remove(), 300);
    }

    // ============ FORMATTING ============
    const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
    // 0 is a real reading (0 °C, 0 km/h). Only null / undefined / NaN count as missing.
    const fmt = (v, unit = '', digits = 1) => isNum(v) ? `${Number(v.toFixed(digits))}${unit}` : `--${unit}`;
    // Wind speed, humidity and light level can never be negative; treat any negative as missing
    const nonNeg = (v) => (isNum(v) && v >= 0) ? v : null;
    const ago = (s) => s < 60 ? `${s}s ago` : s < 3600 ? `${Math.floor(s / 60)}m ago`
                     : s < 86400 ? `${Math.floor(s / 3600)}h ago` : `${Math.floor(s / 86400)}d ago`;

    // ============ CONNECTION STATUS ============
    function setConnectionStatus(status) {
      const el = $('connection-status');
      if (!el) return;
      const labels = { connected: 'Live', connecting: 'Connecting...', disconnected: 'Offline' };
      setClass(el, 'connection-status', status);
      el.innerHTML = `<span class="connection-dot pulse"></span> ${labels[status]}`;
    }

    function markUnavailable() {
      setConnectionStatus('disconnected');
      setText('val-status', 'Unavailable');
      $('val-status').style.color = 'var(--color-warning)';
      document.body.classList.add('is-offline');
    }

    // ============ DATA HANDLING ============
    function animateValueUpdate(element) {
      if (!element) return;
      element.classList.add('updating', 'changed');
      setTimeout(() => {
        element.classList.remove('updating');
        setTimeout(() => element.classList.remove('changed'), 1000);
      }, 300);
    }

    function updateWeatherIcon(rainStatus) {
      const icon = $('weather-icon');
      if (!icon) return;
      const icons = {
        'Rain Detected': 'fa-cloud-showers-heavy',
        'Heavy Rain': 'fa-cloud-showers-heavy',
        'Light Rain': 'fa-cloud-rain',
        'Drizzle': 'fa-cloud-rain',
        'Storm': 'fa-cloud-bolt',
        'No Rain': 'fa-cloud-sun'
      };
      const newClass = icons[rainStatus] || 'fa-cloud-sun';
      const currentClass = icon.querySelector('i')?.className || '';
      if (!currentClass.split(' ').includes(newClass)) {
        icon.classList.add('updating');
        setTimeout(() => {
          icon.innerHTML = `<i class="fas ${newClass}"></i>`;
          icon.classList.remove('updating');
        }, 250);
      }
    }

    function updateAlertBanner(alert) {
      const banner = $('alert-banner');
      const text = $('alert-text');
      if (!banner || !text) return;

      if (alert && alert !== 'Normal') {
        removeClass(banner, 'alert-banner-info', 'alert-banner-warning', 'alert-banner-critical');
        const criticalAlerts = ['Storm Warning', 'Heat Alert', 'Cold Alert'];
        const warningAlerts = ['Low Visibility'];
        if (criticalAlerts.includes(alert)) addClass(banner, 'alert-banner-critical');
        else if (warningAlerts.includes(alert)) addClass(banner, 'alert-banner-warning');
        else addClass(banner, 'alert-banner-info');

        text.innerText = alert;
        addClass(banner, 'alert-active');

        if (alert !== lastAlert) {
          const type = criticalAlerts.includes(alert) ? 'critical' : 'warning';
          showToast(type, 'Weather Alert', alert);
          lastAlert = alert;
        }
      } else {
        removeClass(banner, 'alert-active');
        lastAlert = null;
      }
    }

    function applyData(data) {
      // Error bodies and unexpected payloads must never look "live"
      if (!data || data.error || !data.device_status) { markUnavailable(); return; }

      const online = data.device_status === 'Online';
      document.body.classList.toggle('is-offline', !online);
      setConnectionStatus(online ? 'connected' : 'disconnected');
      setText('val-status', online ? 'Operational' : 'Offline');
      $('val-status').style.color = online ? 'var(--color-primary)' : 'var(--color-danger)';

      if (!('temperature' in data)) {      // database has no readings yet
        setText('val-rain', 'No data yet');
        setText('val-update', 'Last update: never');
        updateAlertBanner(null);
        return;
      }

      const vis = nonNeg(data.visibility);
      const visLabel = { Low: 'Dark', Good: 'Bright' }[data.visibility_status] || 'Not connected';
      const updates = [
        ['val-temp', fmt(data.temperature, '°C')],
        ['val-temp-range', `Range: ${fmt(data.min_temp, '°C')} / ${fmt(data.max_temp, '°C')}`],
        ['val-hum', fmt(nonNeg(data.humidity), '%')],
        ['val-trend', `Temp trend: ${data.trend || '--'}`],
        ['val-wind', fmt(nonNeg(data.wind_speed), ' km/h')],
        ['val-direction', `Direction: ${data.wind_direction || 'N/A'}`],
        ['val-rain', data.rain || 'No data'],
        ['val-vis', fmt(vis, '%', 0)],
        ['val-vis-status', `Light sensor: ${visLabel}`]
      ];

      updates.forEach(([id, value]) => {
        const el = $(id);
        if (el && el.innerText !== value) {
          animateValueUpdate(el);
          el.innerText = value;
        }
      });

      $('vis-bar').style.width = (isNum(vis) ? Math.max(0, Math.min(100, vis)) : 0) + '%';

      const demo = data.device === 'DEMO-SIM';
      const badge = $('device-badge');
      badge.innerText = demo ? `DEMO DATA · ${data.device}` : `Device: ${data.device || '--'}`;
      badge.style.color = demo ? 'var(--color-warning)' : '';
      badge.style.display = 'inline-flex';

      lastUpdate = Date.now() - (data.last_seen_seconds || 0) * 1000;
      lastData = data;
      updateWeatherIcon(data.rain);
      updateAlertBanner(online ? data.alert : null);
    }

    // ============ POLLING ============
    let pollingInterval = null;
    async function fetchData() {
      try {
        const response = await fetch('/api/latest', { cache: 'no-store' });
        const data = await response.json().catch(() => null);
        if (!response.ok) { markUnavailable(); return; }
        applyData(data);
      } catch (error) {
        console.error('Polling error:', error);
        markUnavailable();
      }
    }

    function startPolling() {
      if (pollingInterval) clearInterval(pollingInterval);
      setConnectionStatus('connecting');
      fetchData();
      pollingInterval = setInterval(fetchData, POLL_INTERVAL);
    }

    function setChartEmpty(isEmpty) {
      const el = $('chart-empty');
      if (el) el.hidden = !isEmpty;
    }

    // ============ CHART ============
    async function updateChart() {
      try {
        const response = await fetch(`/api/history?mode=${chartMode}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const historyData = await response.json();

        console.log('[Chart] Raw data:', historyData);

        // Show empty state on chart
        const canvas = $('weatherChart');
        const ctx = canvas.getContext('2d');
        if (!weatherChart) {
          weatherChart = new Chart(ctx, chartConfig);
        }

        // Show empty state when no data
        if (!Array.isArray(historyData) || historyData.length === 0) {
          weatherChart.data.labels = [];
          weatherChart.data.datasets[0].data = [];
          weatherChart.update('active');
          setChartEmpty(true);
          console.warn('[Chart] No data received - showing empty chart');
          return;
        }

        // Filter valid points and parse times safely
        const validPoints = historyData
          .filter(d => d.time && d.temperature !== null && d.temperature !== undefined)
          .map(d => {
            const date = new Date(d.time);
            return {
              time: date,
              temp: Number(d.temperature),
              label: d.label || (chartMode === 'hourly'
                ? date.getHours().toString().padStart(2, '0') + ':00'
                : date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }))
            };
          })
          .filter(d => !isNaN(d.time.getTime()) && !isNaN(d.temp));

        console.log('[Chart] Valid points:', validPoints.length, validPoints);

        if (validPoints.length === 0) {
          const canvas = $('weatherChart');
          const ctx = canvas.getContext('2d');
          if (!weatherChart) {
            weatherChart = new Chart(ctx, chartConfig);
          }
          weatherChart.data.labels = [];
          weatherChart.data.datasets[0].data = [];
          weatherChart.update('active');
          setChartEmpty(true);
          console.warn('[Chart] No valid temperature data after filtering');
          return;
        }

        const labels = validPoints.map(d => d.label);
        const temps = validPoints.map(d => d.temp);

        if (!weatherChart) {
          const canvas = $('weatherChart');
          if (!canvas) {
            console.error('[Chart] Canvas element not found');
            return;
          }
          const ctx = canvas.getContext('2d');
          weatherChart = new Chart(ctx, chartConfig);
        }

        weatherChart.data.labels = labels;
        weatherChart.data.datasets[0].data = temps;
        weatherChart.update('active');

        setChartEmpty(false);
        console.log('[Chart] Updated successfully');
      } catch (error) {
        console.error('[Chart] Error:', error);
      }
    }

    function setChartMode(mode, btn) {
      chartMode = mode;
      document.querySelectorAll('.control-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      updateChart();
    }

    // ============ CLOCK ============
    function updateClock() {
      if (lastUpdate === null) return;
      const sec = Math.max(0, Math.floor((Date.now() - lastUpdate) / 1000));
      setText('val-update', `Last update: ${ago(sec)}`);
    }

    // ============ INIT ============
    function init() {
      startPolling();

      updateChart();
      setInterval(updateClock, 1000);
      setInterval(updateChart, CHART_REFRESH_INTERVAL);
    }

    // DOM ready guard for robust initialization
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }

    // ============ SERVICE WORKER REGISTRATION ============
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/service-worker.js')
          .then((reg) => {
            console.log('[SW] Registered:', reg.scope);

            // Check for updates periodically
            setInterval(() => reg.update(), 60 * 60 * 1000); // hourly

            // Handle updates
            reg.addEventListener('updatefound', () => {
              const newWorker = reg.installing;
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  // New version available - show toast
                  showToast('info', 'Update Available', 'New version ready. Refresh to update.');
                }
              });
            });
          })
          .catch((err) => console.warn('[SW] Registration failed:', err));
      });

      // Listen for controller change (new SW activated)
      const hadController = !!navigator.serviceWorker.controller;
      let refreshing = false;
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (!hadController || refreshing) return;   // first-ever install needs no reload
        refreshing = true;
        window.location.reload();
      });
    }
  
