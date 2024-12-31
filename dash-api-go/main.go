package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"time"

	"github.com/joho/godotenv"
	"github.com/microsoft/ApplicationInsights-Go/appinsights"
	"github.com/stuartleeks/home-dash/dash-api/appinsightsutils"
	"github.com/stuartleeks/home-dash/dash-api/config"
)

func main() {
	fmt.Printf("Server starting...[%d]\n", os.Getpid())

	_, err := os.Stat(".env")
	if err == nil {
		err := godotenv.Load()
		if err != nil {
			log.Fatal("Error loading .env file")
		}
	}

	log.Printf("Dashboard info path: %s", config.GetDashboardInfoPath())
	log.Printf("Messages file path: %s", config.GetMessagesFilePath())

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancel()
	if err := serveAPI(ctx, ":8080"); err != nil && !errors.Is(err, http.ErrServerClosed) {
		fmt.Fprintf(os.Stderr, "Error: %s\n", err)
		os.Exit(1)
	}
	fmt.Println("Server stopped!")
}
func serveAPI(ctx context.Context, address string) error {
	log.Printf("listening on %s", address)
	l, err := net.Listen("tcp", address)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %s\n", err)
		os.Exit(1)
	}

	appInsightsInstrumentationKey := config.GetApplicationInsightsInstrumentationKey()
	if appInsightsInstrumentationKey == "" {
		panic(errors.New("application insights instrumentation key not set"))
	}

	telemetryConfig := appinsights.NewTelemetryConfiguration(appInsightsInstrumentationKey)
	// Configure how many items can be sent in one call to the data collector:
	telemetryConfig.MaxBatchSize = 8192
	// Configure the maximum delay before sending queued telemetry:
	telemetryConfig.MaxBatchInterval = 2 * time.Second

	appInsightsClient := appinsights.NewTelemetryClientFromConfig(telemetryConfig)
	appInsightsClient.Context().Tags.Cloud().SetRole("dash-api-go")

	// appinsights.NewDiagnosticsMessageListener(func(msg string) error {
	// 	fmt.Printf("[%s] %s\n", time.Now().Format(time.UnixDate), msg)
	// 	return nil
	// })

	mux := appinsightsutils.NewServeMuxWithTrace(&appInsightsClient)
	registerHandlers(mux, &appInsightsClient)
	server := &http.Server{
		Addr:    address,
		Handler: mux,
	}
	go func() {
		<-ctx.Done()
		log.Printf("shutting down")
		_ = server.Shutdown(context.Background())
	}()
	return server.Serve(l)
}

func registerHandlers(mux *appinsightsutils.ServeMuxWithTrace, appInsightsClient *appinsights.TelemetryClient) {

	api := NewApiRouter(appInsightsClient)

	mux.HandleFunc("GET /", api.Hello)
	mux.HandleFunc("GET /messages/{date}", api.MessageGet)
	mux.HandleFunc("PUT /messages/{date}", api.MessageSet)
	mux.HandleFunc("GET /temperatures/{id}", api.TemperatureGet)
	mux.HandleFunc("PUT /temperatures/{id}", api.TemperatureSet)
	mux.HandleFunc("GET /leaf", api.LeafDataGet)
	mux.HandleFunc("GET /weather", api.WeatherDataGet)
	mux.HandleFunc("GET /dashboard-data", api.DashboardDataGet)
	mux.HandleFuncWithContext("GET /dashboard-image", api.DashboardImageGet)
}
