/* ==========================================================================
   GPCA Smart Weather Station - Hardware Configuration
   ========================================================================== */

#ifndef CONFIG_H
#define CONFIG_H

// Network Configuration
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";

// Server Configuration
const char* SERVER_URL = "https://gpca-weather-station.onrender.com/api/data";
const char* API_KEY    = "gpcaweatherstation25";

// System Constants
const long DATA_INTERVAL = 12000; // 12 seconds

#endif
