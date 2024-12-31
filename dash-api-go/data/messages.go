package data

import (
	"time"

	"github.com/stuartleeks/home-dash/dash-api/config"
)

func GetMessage(date time.Time) (string, error) {
	messages, err := JsonReadSharedLock[map[string]string](config.GetMessagesFilePath())
	if err != nil {
		return "", err
	}
	return (*messages)[date.Format("2006-01-02")], nil
}

func SetMessage(date time.Time, message string) error {
	err := JsonUpdateExclusiveLock(config.GetMessagesFilePath(), func(messages *map[string]string) error {
		(*messages)[date.Format("2006-01-02")] = message
		return nil
	})
	return err
}
