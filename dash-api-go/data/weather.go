package data

type WeatherDataPoint struct {
	Time         string   `json:"time"`
	Description  string   `json:"description"`
	Temperature  float32  `json:"temperature"`
	FeelsLike    float32  `json:"feels_like"`
	IconPath     string   `json:"icon_path"`
	WindSpeedMph *float32 `json:"wind_speed_mph"`
	WindGustMph  *float32 `json:"wind_gust_mph"`
	Humidity     float32  `json:"humidity"`
}

type WeatherData struct {
	Current  WeatherDataPoint   `json:"current"`
	Forecast []WeatherDataPoint `json:"forecast"`
}

func GetWeatherData() (*WeatherData, error) {
	weatherData, err := JsonReadSharedLock[WeatherData]("weather-summary.json")
	if err != nil {
		return nil, err
	}
	return weatherData, nil
}
