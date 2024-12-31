package appinsightsutils

import "net/http"

// ResponseWriterWithStatusCode is a wrapper around http.ResponseWriter that captures the status code
type ResponseWriterWithStatusCode struct {
	http.ResponseWriter
	statusCode int
}

func NewResponseWriterWithStatusCode(w http.ResponseWriter) *ResponseWriterWithStatusCode {
	return &ResponseWriterWithStatusCode{w, 200}
}
func (w *ResponseWriterWithStatusCode) WriteHeader(statusCode int) {
	w.statusCode = statusCode
	w.ResponseWriter.WriteHeader(statusCode)
}
func (w *ResponseWriterWithStatusCode) StatusCode() int {
	return w.statusCode
}
