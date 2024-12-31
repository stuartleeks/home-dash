package appinsightsutils

import (
	"fmt"
	"net/http"
	"time"

	"github.com/microsoft/ApplicationInsights-Go/appinsights"
)

type ServeMuxWithTrace struct {
	*http.ServeMux
	appInsightsClient *appinsights.TelemetryClient
}

func NewServeMuxWithTrace(appInsightsClient *appinsights.TelemetryClient) *ServeMuxWithTrace {
	return &ServeMuxWithTrace{
		ServeMux:          http.NewServeMux(),
		appInsightsClient: appInsightsClient,
	}
}

// TODO: wrap Handle()
func (mux *ServeMuxWithTrace) HandleFunc(pattern string, handler func(http.ResponseWriter, *http.Request)) {
	mux.ServeMux.HandleFunc(pattern, traceHttpFunc(mux.appInsightsClient, pattern, handler))
}
func (mux *ServeMuxWithTrace) HandleFuncWithContext(pattern string, handler func(http.ResponseWriter, *http.Request, *appinsights.RequestTelemetry)) {
	mux.ServeMux.HandleFunc(pattern, traceHttpFuncWithContext(mux.appInsightsClient, pattern, handler))
}

func traceHttpFunc(appInsightsClient *appinsights.TelemetryClient, name string, fn func(http.ResponseWriter, *http.Request)) http.HandlerFunc {
	return traceHttpFuncWithContext(appInsightsClient, name, func(w http.ResponseWriter, r *http.Request, _ *appinsights.RequestTelemetry) {
		fn(w, r)
	})
}
func traceHttpFuncWithContext(appInsightsClient *appinsights.TelemetryClient, name string, fn func(http.ResponseWriter, *http.Request, *appinsights.RequestTelemetry)) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		scheme := "https"
		if r.TLS == nil {
			scheme = "http"
		}
		telemetry := appinsights.NewRequestTelemetry(r.Method, fmt.Sprintf("%s://%s%s", scheme, r.Host, r.URL.Path), 0*time.Second, "200")
		startTime := time.Now().UTC()

		wrappedResponseWriter := NewResponseWriterWithStatusCode(w)
		fn(wrappedResponseWriter, r, telemetry)

		duration := time.Since(startTime)
		telemetry.Duration = duration
		telemetry.ResponseCode = fmt.Sprintf("%d", wrappedResponseWriter.StatusCode())
		telemetry.Name = name

		(*appInsightsClient).Track(telemetry)
	}
}
