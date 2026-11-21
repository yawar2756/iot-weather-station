# 🌩️☔ The GPCA Weather Station Playground

### *"Where Clouds Get Their Data"*

---

## 🧪 Console Test Data — Auto-Updating Weather Simulator

> **Mission:** Break the sky. Make it rain data. Ignite the charts.

To test your dashboard without real hardware, run this **magical incantation** in your browser console (F12 → Console):

```javascript
// ⚡ THE WEATHER ORACLE ⚡
(async () => {
  const API = 'https://your-render-url.com/api/seed?key=gpcaweatherstation25';
  
  // 🔮 Summon a fresh reading
  const summon = async () => {
    const r = await fetch(`${API}?key=gpcaweatherstation25&live=1`, {
      method: 'POST',
      headers: { 'x-api-key': 'gpcaweatherstation25' }
    });
    const d = await r.json();
    console.log(`🌦️ Weather refreshed:`, d);
    return d;
  };

  // 🚀 Launch the storm
  const storm = summon();
  setInterval(storm, 30000);
  
  console.log('☔ Weather oracle activated — refreshing every 30s ⚡');
})();
```

### 📜 Terminal Version (The Shaman's Ritual):

```bash
# Run this in your terminal to feel the data flow
while true; do
  curl -s -X POST "https://your-render-url.com/api/seed?key=gpcaweatherstation25&live=1" \
    -H "x-api-key: gpcaweatherstation25" \
    -H "Content-Type: application/json" | jq '.'
  sleep 30
done
```

---

## 🎨 Creative License

*Weather Station Simulator v1.0 — Engineered with ❄️🔥⚡ by the GPCA IoT Lab*
