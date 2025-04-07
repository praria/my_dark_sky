import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///weather.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENWEATHER_API_KEY = os.getenv("API_KEY", "*********")

config = Config()
