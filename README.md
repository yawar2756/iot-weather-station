# GPCA Weather Station - Console Test Data Automation

To generate automatically updating console test data that changes every 30 seconds:

## Method 1: Browser Console (Recommended)

Open your browser's developer console (F12) and run this JavaScript snippet:

```javascript
// Set your Render URL if different
const API_URL = 'https://your-render-url.com/api/seed';

async function updateLiveData() {
  try {
    const response = await fetch(`${API_URL}?key=gpcaweatherstation25&live=1`, {
      method: 'POST',
      headers: {
        'x-api-key': 'gpcaweatherstation25'
      }
    });
    const data = await response.json();
    console.log('Live data updated:', data);
  } catch (error) {
    console.error('Error updating data:', error);
  }
}

// Update every 30 seconds
setInterval(updateLiveData, 30000);
console.log('Live data automation started - updates every 30 seconds');
```

## Method 2: Terminal (cURL)

Run this command repeatedly in your terminal:

```bash
while true; do
  curl -X POST "https://your-render-url.com/api/seed?key=gpcaweatherstation25&live=1" \
    -H "x-api-key: gpcaweatherstation25" \
    -s | jq '.temperature, .humidity, .wind_speed, .wind_direction'
  sleep 30
done
```

## Notes:
- This inserts fresh readings at current time (simulating live sensor data)
- Dashboard will show "Online" status with new values
- Chart.js will automatically update with new data
- Stop with Ctrl+C when done
- Uses existing `/api/seed` endpoint - no code changes needed