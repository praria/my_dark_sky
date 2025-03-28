from flask import Flask, request, render_template, jsonify
import requests
import json
import os
import time
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
from config import config

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# OpenWeather API Key (Free-tier)
API_KEY = config.OPENWEATHER_API_KEY

DEFAULT_LOCATION = "Raleigh"

# Cache setup
CACHE_FILE = "cache/weather_cache.json"
CACHE_EXPIRY = 300  # 5 minutes

# Database Model for Notifications
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    preferences = db.Column(db.String(255), nullable=False)

with app.app_context():
    db.create_all()

def load_cache():
    """Load the cache from a JSON file, return an empty dict if not found or invalid."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {}

def save_cache(cache):
    """Save the cache to a JSON file."""
    with open(CACHE_FILE, "w") as file:
        json.dump(cache, file)

def get_weather(location):
    cache = load_cache()
    cache_key = f"{location}_forecast"

    # Check if data is cached and still valid
    if cache_key in cache and time.time() - cache[cache_key]["timestamp"] < CACHE_EXPIRY:
        print("⏳ Using cached data")
        return cache[cache_key]["data"]

    # Step 1: Get location's latitude and longitude
    geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={API_KEY}"
    response = requests.get(geocode_url)
    geo_data = response.json()

    if not geo_data:
        return {"error": "Invalid location. Please try again."}

    lat = geo_data[0]['lat']
    lon = geo_data[0]['lon']

    # Step 2: Fetch current weather
    current_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    current_response = requests.get(current_url)
    current_data = current_response.json()

    # Step 3: Fetch 5-day forecast (Every 3-hour intervals)
    forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    forecast_response = requests.get(forecast_url)
    forecast_data = forecast_response.json()
    print(f"forecast_data: {forecast_data}")

    if "main" not in current_data or "list" not in forecast_data:
        return {"error": "Weather data not available."}

    # Step 4: Process the current weather
    sunrise = datetime.fromtimestamp(current_data["sys"]["sunrise"], tz=timezone.utc).strftime('%H:%M:%S')
    sunset = datetime.fromtimestamp(current_data["sys"]["sunset"], tz=timezone.utc).strftime('%H:%M:%S')


    result = {
        "location": location,
        "current": {
            "temperature": current_data["main"]["temp"],
            "real_feel": current_data["main"]["feels_like"],
            "humidity": current_data["main"]["humidity"],
            "wind_speed": current_data["wind"]["speed"],
            "wind_direction": current_data["wind"]["deg"],
            "pressure": current_data["main"]["pressure"],
            "visibility": current_data.get("visibility", "N/A"),
            "sunrise": sunrise,
            "sunset": sunset,
            "weather": current_data["weather"][0]["description"],
        },
        "forecast": []
    }

    # Step 5: Process the 6-day forecast
    daily_forecast = {}
    today = datetime.now(tz=timezone.utc).date()



    for entry in forecast_data["list"]:
        date = datetime.fromtimestamp(entry["dt"], tz=timezone.utc).date()
        if date not in daily_forecast and date > today:
            daily_forecast[date] = {
                "temperature": entry["main"]["temp"],
                "real_feel": entry["main"]["feels_like"],
                "humidity": entry["main"]["humidity"],
                "wind_speed": entry["wind"]["speed"],
                "weather": entry["weather"][0]["description"],
            }

        if len(daily_forecast) >= 6:  
            break

    result["forecast"] = [{"date": str(date), **data} for date, data in daily_forecast.items()]

    # Step 6: Cache the result and save
    cache[cache_key] = {
        "timestamp": time.time(),
        "data": result
    }
    save_cache(cache)

    return result

@app.route('/')
def index():
    return render_template("index.html")

@app.route("/weather", methods=["GET"])
def weather():
    location = request.args.get("location", default=DEFAULT_LOCATION, type=str)
    date = request.args.get("date", type=str)

    # Check if a specific date is provided (either future or historical)
    if date:
        data = get_weather_on_date(location, date)
    else:
        data = get_weather(location)

    if data:
        return jsonify(data)
    return jsonify({"error": "Could not fetch weather"}), 500

def get_weather_on_date(location, date_str):
    """Fetch weather data for a specific past or future date."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()

        # Step 1: Get latitude & longitude for the location
        geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={API_KEY}"
        response = requests.get(geocode_url)
        geo_data = response.json()

        if not geo_data:
            return {"error": "Invalid location. Please try again."}

        lat, lon = geo_data[0]['lat'], geo_data[0]['lon']

        # Step 2: Fetch data based on whether the date is in the past or future
        if target_date < today:
            # Handle past weather (only available for last 5 days)
            max_history_days = 5
            oldest_date = today - timedelta(days=max_history_days)

            if target_date < oldest_date:
                return {"error": "Historical weather data is only available for the past 5 days."}

            # Fetch historical weather data
            # Convert to datetime at 00:00:00 UTC
            midnight_utc = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
            midnight_timestamp = int(midnight_utc.timestamp())

            # Convert to datetime at 23:00:00 UTC
            late_night_utc = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=0, tzinfo=timezone.utc)
            late_night_timestamp = int(late_night_utc.timestamp())
            
            timestamp = int(datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc).timestamp())
            history_url = f"https://history.openweathermap.org/data/2.5/history/city?lat={lat}&lon={lon}&type=hour&start={midnight_timestamp}&end={late_night_timestamp}&appid={API_KEY}&units=metric"
            history_response = requests.get(history_url)
            history_data = history_response.json()
            print(history_data)

            if "list" not in history_data:
                return {"error": "Historical weather data is unavailable for this date."}

            # Extract min/max temp, humidity, wind speed, and weather description
            temp_min = float("inf")
            temp_max = float("-inf")
            humidity = None
            wind_speed = None
            weather_desc = None

            for entry in history_data["list"]:
                entry_date = datetime.fromtimestamp(entry["dt"], tz=timezone.utc).date()

                if entry_date == target_date:
                    temp_min = min(temp_min, entry["main"]["temp_min"])
                    temp_max = max(temp_max, entry["main"]["temp_max"])
                    humidity = entry["main"]["humidity"]
                    wind_speed = entry["wind"]["speed"]
                    weather_desc = entry["weather"][0]["description"]

            if temp_min == float("inf") or temp_max == float("-inf"):
                return {"error": "No historical data found for this date."}

            result = {
                "location": location,
                "date": date_str,
                "temp_min": temp_min,
                "temp_max": temp_max,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "weather": weather_desc,
            }

        else:
            # Handle future weather (OpenWeather provides only a 5-day forecast)
            max_forecast_days = 5
            last_forecast_date = today + timedelta(days=max_forecast_days)

            if target_date > last_forecast_date:
                return {"error": "Forecast data is only available for the next 5 days."}

            # Fetch forecast data
            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
            forecast_response = requests.get(forecast_url)
            forecast_data = forecast_response.json()

            if "list" not in forecast_data:
                return {"error": "No forecast data available."}

            # Process 3-hourly data into daily summaries
            daily_forecast = {}
            for entry in forecast_data["list"]:
                forecast_datetime = datetime.fromtimestamp(entry["dt"], tz=timezone.utc).date()

                if forecast_datetime >= today:
                    if forecast_datetime not in daily_forecast:
                        daily_forecast[forecast_datetime] = {
                            "temp_min": entry["main"]["temp"],
                            "temp_max": entry["main"]["temp"],
                            "humidity": entry["main"]["humidity"],
                            "wind_speed": entry["wind"]["speed"],
                            "weather": entry["weather"][0]["description"],
                        }
                    else:
                        daily_forecast[forecast_datetime]["temp_min"] = min(
                            daily_forecast[forecast_datetime]["temp_min"], entry["main"]["temp"]
                        )
                        daily_forecast[forecast_datetime]["temp_max"] = max(
                            daily_forecast[forecast_datetime]["temp_max"], entry["main"]["temp"]
                        )

            # Check if requested date exists in forecast
            if target_date in daily_forecast:
                result = {
                    "location": location,
                    "date": date_str,
                    **daily_forecast[target_date]
                }
            else:
                return {"error": "No forecast data available for this date."}

        return result

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


if __name__ == '__main__':
    app.run(debug=True)
