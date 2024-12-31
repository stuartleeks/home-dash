package data

import "time"

type Action struct {
	ID          string
	DisplayName string
}
type DashboardData struct {
	Message     string
	DateString  string
	LeafData    *LeafData
	WeatherData *WeatherData
	Pistat0     *Temperature
	Actions     []Action
	GeneratedAt time.Time
}

const (
	ACTION_REFRESH = "refresh"
)

func GetDashboardData() (*DashboardData, error) {
	message, err := GetMessage(time.Now().UTC())
	if err != nil {
		return nil, err
	}
	leafData, err := GetLeafData()
	if err != nil {
		return nil, err
	}
	weatherData, err := GetWeatherData()
	if err != nil {
		return nil, err
	}
	weatherData.Forecast = weatherData.Forecast[:3]
	temperatureData, err := GetTemperature("pistat-0")
	if err != nil {
		return nil, err
	}
	return &DashboardData{
		Message:     message,
		DateString:  time.Now().UTC().Format("Monday, 02 January 2006"),
		LeafData:    leafData,
		WeatherData: weatherData,
		Pistat0:     temperatureData,
		Actions: []Action{
			{ID: ACTION_REFRESH, DisplayName: "Refresh"},
		},
		GeneratedAt: time.Now().UTC(),
	}, nil
}
