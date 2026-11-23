/* ==========================================================================
   GPCA Smart Weather Station - Hardware Configuration
   ========================================================================== */

#ifndef CONFIG_H
#define CONFIG_H

// Network Configuration - EDIT THESE VALUES
const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";

// Server Configuration
const char* SERVER_URL = "https://gpca-weather-station.onrender.com/api/data";
// API_KEY must be set in config.private.h (not committed to git)
// #include "config.private.h"

// Device Identity (for multi-station support)
const char* DEVICE_ID  = "GPCA-STATION-01";

// System Constants
const long DATA_INTERVAL = 12000; // 12 seconds

#endif