# Welcome to My Dark Sky
***************************

## Task
Implementation of a Flask-based Weather web application that provides real-time weather updates, 5-day forecasts,
5-day historical weather data for any location. The app fetches data from the OpenWeather API (free version) 
and presents it with a modern UI using Tailwind CSS 

## Description
1. Current Weather Information and 5-day Weather forecast for a given location (default location: Raleigh):
- It gives real-time temperature, feels-like temperature, wind speed, wind direction, humidity, visibility, pressure, sunrise, and sunset for a location.
- It provides a 5-day forecast with daily min/max temperature, wind speed, and weather conditions and It ensures efficient data fetching by caching results.

2.  Historical & Future Weather lookup:
- Allows user to search for past or future weather by selecting a date and location 

3. Data caching for performance:
- It uses an in-memory JSON cache to store weather for 5 minutes, reducing API resquests.


### features planned to build in future:
- Hourly forcast
- Push Notifications for severe weather alerts

## Installation
1.  clone the repository from github
- git clone https://git.us.qwasar.io/my_dark_sky_180134_gmagww/my_dark_sky.git

2. create a virtual environment
- python -m venv myvenv
- source myvenv/bin/activate

3. Install Dependencies:
- pip install -r requirements.txt

4. configure API key
 - set up the API_KEY = "OpenWeather_api_key"

5. run the application
- python3 app.py


## Usage
copy the URL from the following file and paste it in the browser:
my_dark_sky_url.txt

### The Core Team
-- Prakash Shrestha -- 