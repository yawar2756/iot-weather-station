/* ==========================================================================
   GPCA Smart Weather Station - Hardware Configuration
   ========================================================================== */

#ifndef CONFIG_H
#define CONFIG_H

// Network Configuration
const char* WIFI_SSID = "R";
const char* WIFI_PASS = "11111100";

// Server Configuration
const char* SERVER_URL = "https://gpca-weather-station.onrender.com/api/data";
const char* API_KEY    = "gpcaweatherstation25";

// Device Identity (for multi-station support)
const char* DEVICE_ID  = "GPCA-STATION-01";

// System Constants
const long DATA_INTERVAL = 12000; // 12 seconds

#endif
