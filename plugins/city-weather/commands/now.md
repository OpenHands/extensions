---
allowed-tools: Bash(curl:*)
argument-hint: <city>
description: Get current weather, time, and precipitation forecast for a city
---

# City Weather Report

Get the current time, temperature (in both Fahrenheit and Celsius), and precipitation forecast for the next 4 hours for the specified city.

## Instructions

1. Parse the city name from the arguments: **$ARGUMENTS**

2. Use the Open-Meteo Geocoding API to find the city coordinates:
   ```bash
   curl -s "https://geocoding-api.open-meteo.com/v1/search?name=CITY_NAME&count=1&language=en&format=json"
   ```
   Replace `CITY_NAME` with the URL-encoded city name.

3. Extract the latitude, longitude, and timezone from the response.

4. Use the Open-Meteo Weather API to fetch current weather and hourly forecast:
   ```bash
   curl -s "https://api.open-meteo.com/v1/forecast?latitude=LAT&longitude=LON&current=temperature_2m,precipitation&hourly=temperature_2m,precipitation_probability&timezone=TIMEZONE&forecast_hours=4"
   ```
   Replace `LAT`, `LON`, and `TIMEZONE` with the values from step 3.

5. Format and present the results in a clear report:

   **City Weather Report for [City Name]**
   
   - **Current Time:** [formatted local time in the city's timezone]
   - **Temperature:** [X]°F / [Y]°C
   - **Current Precipitation:** [amount] mm
   
   **Precipitation Forecast (Next 4 Hours):**
   | Time | Probability |
   |------|-------------|
   | [hour 1] | [X]% |
   | [hour 2] | [Y]% |
   | [hour 3] | [Z]% |
   | [hour 4] | [W]% |

## Example Usage

`/city-weather:now New York`
`/city-weather:now Tokyo`
`/city-weather:now London`

## Notes

- Uses the free Open-Meteo API (no API key required)
- Temperature is provided in both Fahrenheit and Celsius
- Precipitation probability is shown for the next 4 hours
- Times are displayed in the city's local timezone
