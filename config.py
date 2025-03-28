import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///weather.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENWEATHER_API_KEY = os.getenv("API_KEY", "fd54da6db63cb2fe6d24b34b2efa3c50")

config = Config()
