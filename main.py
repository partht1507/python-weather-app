import datetime
import requests
import string
from flask import Flask, render_template, request, redirect, url_for
import os
from dotenv import load_dotenv
import openai
import re  # Import regex to validate city name format


load_dotenv()

api_key = os.getenv("OWM_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Set OpenAI API key
openai.api_key = openai_api_key

# OpenWeatherMap API endpoints
OWM_ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_ENDPOINT = "https://api.openweathermap.org/data/2.5/forecast"
GEOCODING_API_ENDPOINT = "http://api.openweathermap.org/geo/1.0/direct"

app = Flask(__name__)

# Function to extract city from user input using the new OpenAI API (v1.0.0+)

def extract_city_from_text(user_text):
    # Define the system and user messages for the new API
    messages = [
        {"role": "system", "content": "You are a helpful assistant that extracts city names from user queries. You have to answer just the city name. No extra text PLEASE. Make sure its a CITY and not a country. You can also suggest other cities if you think something matches."},
        {"role": "user", "content": f"The user asked: '{user_text}'. Please think and extract the city name for this query."}
    ]
    
    # Call the ChatCompletion API
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=10
    )
    city_name = response['choices'][0]['message']['content'].strip()

    # Check if the response contains a valid city name (simple check using regex for alphabetic words)
    if re.match(r"^[A-Za-z\s\-]+$", city_name):
        return city_name
    else:
        # If the response doesn't look like a city, return the message in a fun way
        return f"Oops! Looks like I couldn't find the city you are looking for. But here's what I got: '{city_name}'. Try asking again!"



# Home page: asks the user to input a city or query text
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        user_input = request.form.get("search")
        
        # Extract city using GPT
        city_or_message = extract_city_from_text(user_input)
        print(city_or_message)
        # Check if the result is a valid city or a message (invalid city)
        if "Oops!" in city_or_message:
            return render_template("error.html", error_message=city_or_message)
        else:
            return redirect(url_for("get_weather", city=city_or_message))
    
    return render_template("index.html")


# Weather information page: displays the weather for the given city
@app.route("/<city>", methods=["GET", "POST"])
def get_weather(city):
    city_name = string.capwords(city)
    today = datetime.datetime.now()
    current_date = today.strftime("%A, %B %d")

    # Get latitude and longitude for city
    location_params = {
        "q": city_name,
        "appid": api_key,
        "limit": 3,
    }

    location_response = requests.get(GEOCODING_API_ENDPOINT, params=location_params)
    location_data = location_response.json()

    # Handle error if no coordinates are returned
    if not location_data:
        return redirect(url_for("error"))

    lat = location_data[0]['lat']
    lon = location_data[0]['lon']

    # Get weather data
    weather_params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
    }
    weather_response = requests.get(OWM_ENDPOINT, weather_params)
    weather_data = weather_response.json()

    # Get current weather details
    current_temp = round(weather_data['main']['temp'])
    current_weather = weather_data['weather'][0]['main']
    min_temp = round(weather_data['main']['temp_min'])
    max_temp = round(weather_data['main']['temp_max'])
    wind_speed = weather_data['wind']['speed']

    # Get 5-day forecast
    forecast_response = requests.get(OWM_FORECAST_ENDPOINT, weather_params)
    forecast_data = forecast_response.json()

    # Prepare lists of temperature and weather descriptions for 5-day forecast
    five_day_temp_list = [round(item['main']['temp']) for item in forecast_data['list'] if '12:00:00' in item['dt_txt']]
    five_day_weather_list = [item['weather'][0]['main'] for item in forecast_data['list'] if '12:00:00' in item['dt_txt']]

    # Get dates for the next 5 days
    five_day_dates_list = [(today + datetime.timedelta(days=i)).strftime("%A") for i in range(5)]
    
    # Zip the lists in the backend for easier iteration
    five_day_forecast = zip(five_day_dates_list, five_day_temp_list, five_day_weather_list)

    # Render the city weather template
    return render_template(
        "city.html",
        city_name=city_name,
        current_date=current_date,
        current_temp=current_temp,
        current_weather=current_weather,
        min_temp=min_temp,
        max_temp=max_temp,
        wind_speed=wind_speed,
        five_day_forecast=five_day_forecast
    )

# Error page: handles invalid city input
@app.route("/error")
def error():
    return render_template("error.html")

if __name__ == "__main__":
    app.run(debug=True)
