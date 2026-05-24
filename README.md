# 🚗⛽ Fuel Checker - Automated Fuel Optimizer

A Streamlit app that finds the cheapest fuel stations on your route and optimizes your journey.

## Features

✅ **Real-time Fuel Prices** - Fetches live fuel prices from FuelCheck NSW API  
✅ **Route Optimization** - Uses TomTom API to calculate detours  
✅ **Cost Comparison** - Shows savings vs. cheapest option  
✅ **Navigation Integration** - Direct Waze links to selected stations  
✅ **Trip Summary** - Distance, time, and fuel consumption estimates  

## Setup

### 1. Get API Keys

- **FuelCheck API**: Register at https://fuelcheck.nsw.gov.au/api
- **TomTom API**: Register at https://developer.tomtom.com

### 2. Install Dependencies

```bash
pip install -r requirement.txt
```

### 3. Configure API Keys

Create a `.env` file in the project root:

```
FUELCHECK_API_KEY=your_fuelcheck_api_key
TOMTOM_API_KEY=your_tomtom_api_key
```

### 4. Run the App

```bash
streamlit run fuel_finder.py
```

## Project Structure

```
fuel_checker/
├── fuel_finder.py          # Main Streamlit app
├── config.py               # Configuration & API keys
├── api_fuelcheck.py        # FuelCheck API integration
├── api_tomtom.py           # TomTom routing integration
├── navigation.py           # URL generators (Waze, Google Maps)
├── requirement.txt         # Python dependencies
├── .env                    # API keys (DO NOT COMMIT)
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Usage

1. Enter your starting address and destination
2. Set your car's fuel economy (L/100km)
3. Set your fuel tank capacity
4. Enter current fuel level
5. Click "🚀 Auto-Scan & Optimize"
6. View results and click "Open Waze" to navigate

## API Documentation

### FuelCheck NSW
- Base URL: `https://fuelcheck.nsw.gov.au/api/v1`
- Docs: https://fuelcheck.nsw.gov.au/api

### TomTom
- Routing API: https://api.tomtom.com/routing/1/calculateRoute
- Search API: https://api.tomtom.com/search/2/geocode/
- Docs: https://developer.tomtom.com

## License

MIT

## Support

For issues, create a GitHub issue or contact the maintainer.
