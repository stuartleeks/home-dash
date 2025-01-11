package main

import (
	"bytes"
	"crypto/sha1"
	"encoding/json"
	"fmt"
	"image/jpeg"
	"log"
	"math"
	"net/http"
	"os"
	"time"

	"github.com/microsoft/ApplicationInsights-Go/appinsights"
	"github.com/stuartleeks/home-dash/dash-api/data"
)

type ApiRouter struct {
	appInsightsClient *appinsights.TelemetryClient
	dataCache         *data.Cache[string, data.DashboardData]
}

func NewApiRouter(appInsightsClient *appinsights.TelemetryClient) *ApiRouter {
	if appInsightsClient == nil {
		panic("appInsightsClient is required")
	}
	return &ApiRouter{
		appInsightsClient: appInsightsClient,
		dataCache:         data.NewCache[string, data.DashboardData](10 * time.Minute),
	}
}

func (api *ApiRouter) Hello(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		w.WriteHeader(http.StatusNotFound)
		w.Write([]byte("Not Found"))
		return
	}
	fmt.Fprintf(w, "Hello, world 👋")
}

func (api *ApiRouter) MessageGet(w http.ResponseWriter, r *http.Request) {
	dateString := r.PathValue("date")
	date, err := time.Parse("2006-01-02", dateString)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	message, err := data.GetMessage(date)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	_ = json.NewEncoder(w).Encode(struct {
		Message string `json:"message"`
	}{
		Message: message,
	})
}

func (api *ApiRouter) MessageSet(w http.ResponseWriter, r *http.Request) {
	dateString := r.PathValue("date")
	date, err := time.Parse("2006-01-02", dateString)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	var message struct {
		Message string `json:"message"`
	}
	err = json.NewDecoder(r.Body).Decode(&message)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	err = data.SetMessage(date, message.Message)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
}

func (api *ApiRouter) TemperatureGet(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	temperature, err := data.GetTemperature(id)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	_ = json.NewEncoder(w).Encode(temperature)
}

func (api *ApiRouter) TemperatureSet(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	var temperature struct {
		Temperature float32 `json:"temperature"`
		Humidity    float32 `json:"humidity"`
	}
	err := json.NewDecoder(r.Body).Decode(&temperature)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	err = data.SetTemperature(id, data.Temperature{
		ReportedAt:  data.ReportedAt(time.Now().UTC()),
		Temperature: temperature.Temperature,
		Humidity:    temperature.Humidity,
	})
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
}

func (api *ApiRouter) LeafDataGet(w http.ResponseWriter, r *http.Request) {
	leafData, err := data.GetLeafData()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	err = json.NewEncoder(w).Encode(leafData)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
}

func (api *ApiRouter) WeatherDataGet(w http.ResponseWriter, r *http.Request) {
	weatherData, err := data.GetWeatherData()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	err = json.NewEncoder(w).Encode(weatherData)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
}

func (api *ApiRouter) DashboardDataGet(w http.ResponseWriter, r *http.Request) {
	dashboardData, err := data.GetDashboardData()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	err = json.NewEncoder(w).Encode(dashboardData)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
}

func (api *ApiRouter) trackCacheEvent(cacheHit bool, reason string) {
	e := appinsights.NewEventTelemetry("cache-hit")
	e.Properties["cache-hit"] = fmt.Sprintf("%t", cacheHit)
	e.Properties["reason"] = reason
	(*api.appInsightsClient).Track(e)
}
func (api *ApiRouter) DashboardImageGet(w http.ResponseWriter, r *http.Request, telemetry *appinsights.RequestTelemetry) {
	// TODO logging/metrics
	log.Println("DashboardImageGet starting...")
	defer log.Println("DashboardImageGet done.")

	actionId := r.Header.Get("action-id")
	if actionId != "" {
		log.Printf("Action id: %s", actionId)
		telemetry.Properties["action-id"] = actionId
		// TODO handle actions
	}

	ifNoneMatch := r.Header.Get("If-None-Match")
	if ifNoneMatch != "" {
		log.Printf("If-None-Match: %s", ifNoneMatch)
		telemetry.Properties["If-None-Match"] = ifNoneMatch
	}

	dashboardData, err := data.GetDashboardData()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Calculate mins to sleep and write header
	now := time.Now()
	minsToSleep := 5
	currentHour := now.Hour()
	if currentHour >= 22 || currentHour < 6 {
		// Sleep until 6am
		minsToSleep = 60 * (6 - currentHour)
		if minsToSleep < 0 {
			minsToSleep += 24 * 60
		}
	}

	log.Printf("minsToSleep: %d", minsToSleep)
	telemetry.Properties["mins-to-sleep"] = fmt.Sprintf("%d", minsToSleep)
	w.Header().Set("mins-to-sleep", fmt.Sprintf("%d", minsToSleep))

	var cachedDashboardData *data.DashboardData
	if ifNoneMatch != "" && actionId == "" {
		// Only cache if we have an action id
		// and if the caller sent an If-None-Match header (i.e. they're not trying to cache)

		// Get cached data
		cachedDashboardData = api.dataCache.Get(ifNoneMatch)

		if cachedDashboardData != nil {
			log.Println("Found cached data")
			reason := checkForSignificantChange(cachedDashboardData, dashboardData)
			if reason == "" {
				api.trackCacheEvent(true, "no-significant-change")
				w.WriteHeader(http.StatusNotModified)
				return
			}
			log.Printf("Significant change in data: %s", reason)
			api.trackCacheEvent(false, reason)
			telemetry.Properties["cache-invalid"] = reason
		} else {
			api.trackCacheEvent(false, "no cached data")
			log.Println("No cached data")
		}
	} else {
		if actionId == "" {
			api.trackCacheEvent(false, fmt.Sprintf("Got action-id: %s", actionId))
		} else {
			api.trackCacheEvent(false, "If-None-Match header not set")
		}
	}

	dc, err := drawDashboardImage(dashboardData)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "image/jpeg")

	// Can't use multiwriter here because we need the hash to set
	// the etag header before writing the image to the response
	buf := new(bytes.Buffer)

	if err = dc.EncodeJPG(buf, &jpeg.Options{Quality: 100}); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	bufBytes := buf.Bytes()

	hash := sha1.New()
	hash.Write(bufBytes)
	hashValue := fmt.Sprintf("%x", hash.Sum(nil))

	// Cache the data and return the etag
	api.dataCache.Set(hashValue, dashboardData)
	log.Printf("Etag: %s", hashValue)
	telemetry.Properties["Etag"] = hashValue
	w.Header().Set("Etag", hashValue)

	actionIDs := []string{}
	for _, action := range dashboardData.Actions {
		actionIDs = append(actionIDs, action.ID)
	}
	actionIDsEncoded, err := json.Marshal(actionIDs)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("actions", string(actionIDsEncoded))

	_, _ = w.Write(bufBytes)
}

func checkForSignificantChange(oldData *data.DashboardData, newData *data.DashboardData) string {
	if err := json.NewEncoder(os.Stdout).Encode(oldData); err != nil {
		panic(err) // TODO - handle
	}
	if err := json.NewEncoder(os.Stdout).Encode(newData); err != nil {
		panic(err) // TODO - handle
	}

	if oldData == nil {
		return "oldData is nil"
	}

	if newData.GeneratedAt.Sub(oldData.GeneratedAt) > 30*time.Minute {
		// If the data is more than 30 minutes old, then it's a significant change
		return "generatedAt is more than 30 minutes apart"
	}

	// Update if charge state etc have changed
	if oldData.LeafData.ChargingStatus != newData.LeafData.ChargingStatus {
		return "ChargingStatus has changed"
	}
	if oldData.LeafData.IsConnected != newData.LeafData.IsConnected {
		return "IsConnected has changed"
	}
	if math.Abs(float64(oldData.LeafData.CruisingRangeAcOffMiles-newData.LeafData.CruisingRangeAcOffMiles)) > 3 {
		return "cruisingRangeAcOffMiles has changed"
	}

	// Update if the message has changed
	if oldData.Message != newData.Message {
		return "message has changed"
	}

	// Update if pistat0 has changed
	if oldData.IsPiStatDataValid() != newData.IsPiStatDataValid() {
		return "pistat0 validity has changed"
	}
	if math.Abs(float64(oldData.Pistat0.Temperature-newData.Pistat0.Temperature)) > 0.5 {
		return "pistat0 temperature has changed"
	}
	if math.Abs(float64(oldData.Pistat0.Humidity-newData.Pistat0.Humidity)) > 2 {
		return "pistat0 humidity has changed"
	}

	return ""
}
