package config

import (
	"os"
	"path"
)

func GetDashboardInfoPath() string {
	return os.Getenv("DASHBOARD_INPUT_DIR")
}

func GetApplicationInsightsInstrumentationKey() string {
	return os.Getenv("APPLICATIONINSIGHTS_INSTRUMENTATION_KEY")
}

func GetMessagesFilePath() string {
	p := os.Getenv("MESSAGES_FILE")
	if p == "" {
		p = path.Join(GetDashboardInfoPath(), "messages.json")
	}
	return p
}
