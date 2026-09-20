from app.services.weather import WeatherDay, WeatherResult


def test_weather_day_contains_structured_forecast_data():
    weather_day = WeatherDay(
        date="2026-09-18",
        high_celsius=22.5,
        low_celsius=14.0,
        precipitation_probability=30,
        condition="partly cloudy",
    )

    assert weather_day.condition == "partly cloudy"
    assert weather_day.precipitation_probability == 30


def test_weather_result_contains_multiple_days():
    weather_result = WeatherResult(
        destination="Paris",
        latitude=48.8566,
        longitude=2.3522,
        days=[
            WeatherDay(
                date="2026-09-18",
                high_celsius=22.5,
                low_celsius=14.0,
                precipitation_probability=30,
                condition="partly cloudy",
            ),
            WeatherDay(
                date="2026-09-19",
                high_celsius=21.0,
                low_celsius=13.0,
                precipitation_probability=60,
                condition="light rain",
            ),
        ],
    )

    assert weather_result.destination == "Paris"
    assert len(weather_result.days) == 2
    assert weather_result.days[1].condition == "light rain"
