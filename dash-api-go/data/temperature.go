package data

import (
	"fmt"
	"time"
)

type ReportedAt time.Time

const reportedAtFormat = "2006-01-02T15:04:05"

func (r *ReportedAt) UnmarshalJSON(b []byte) error {
	if len(b) < 2 || b[0] != '"' || b[len(b)-1] != '"' {
		return fmt.Errorf("invalid time format: %s", b)
	}
	b = b[1 : len(b)-1]
	t, err := time.Parse(reportedAtFormat, string(b))
	if err != nil {
		return err
	}
	*r = ReportedAt(t)
	return nil
}
func (r ReportedAt) MarshalJSON() ([]byte, error) {
	return []byte(`"` + time.Time(r).Format(reportedAtFormat) + `"`), nil
}

type Temperature struct {
	ReportedAt  ReportedAt `json:"reported_at"`
	Temperature float32    `json:"temperature"`
	Humidity    float32    `json:"humidity"`
}

type temperatures struct {
	Temperatures map[string]Temperature `json:"temperatures"`
}

func GetTemperature(id string) (*Temperature, error) {
	temperatures, err := JsonReadSharedLock[temperatures]("temperatures.json")
	if err != nil {
		return nil, err
	}

	temperature := (*temperatures).Temperatures[id]
	return &temperature, nil
}

func SetTemperature(id string, temperature Temperature) error {
	err := JsonUpdateExclusiveLock[temperatures]("temperatures.json", func(temperatures *temperatures) error {
		(*temperatures).Temperatures[id] = temperature
		return nil
	})
	return err
}
