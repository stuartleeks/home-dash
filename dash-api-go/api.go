package main

import (
	"bytes"
	"crypto/sha1"
	"encoding/json"
	"fmt"
	"image"
	"image/color"
	"image/jpeg"
	"image/png"
	"log"
	"math"
	"net/http"
	"os"
	"path"
	"time"

	"github.com/fogleman/gg"
	"github.com/microsoft/ApplicationInsights-Go/appinsights"
	"github.com/stuartleeks/home-dash/dash-api/data"
	"golang.org/x/image/draw"
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
				w.WriteHeader(http.StatusNotModified)
				return
			}
			log.Printf("Significant change in data: %s", reason)
			telemetry.Properties["cache-invalid"] = reason
		} else {
			log.Println("No cached data or significant change")
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
	if oldData.LeafData.IsCharging != newData.LeafData.IsCharging {
		return "isCharging has changed"
	}
	if oldData.LeafData.IsPluggedIn != newData.LeafData.IsPluggedIn {
		return "isPluggedIn has changed"
	}
	if math.Abs(float64(oldData.LeafData.CruisingRangeAcOffMiles-newData.LeafData.CruisingRangeAcOffMiles)) > 3 {
		return "cruisingRangeAcOffMiles has changed"
	}

	// Update if the message has changed
	if oldData.Message != newData.Message {
		return "message has changed"
	}

	// Update if pistat0 has changed
	if math.Abs(float64(oldData.Pistat0.Temperature-newData.Pistat0.Temperature)) > 0.5 {
		return "pistat0 temperature has changed"
	}
	if math.Abs(float64(oldData.Pistat0.Humidity-newData.Pistat0.Humidity)) > 2 {
		return "pistat0 humidity has changed"
	}

	return ""
}

func drawDashboardImage(dashboardData *data.DashboardData) (*gg.Context, error) {
	width := 800
	height := 480

	img := image.NewRGBA(image.Rect(0, 0, width, height))

	dc := gg.NewContextForRGBA(img)
	dc.SetRGB(1, 1, 1)
	dc.DrawRectangle(0, 0, float64(width), float64(height))
	dc.Fill()

	// font, err := truetype.Parse(goregular.TTF)
	// if err != nil {
	// 	http.Error(w, err.Error(), http.StatusInternalServerError)
	// 	return
	// }
	// fontFace := truetype.NewFace(font, &truetype.Options{
	// 	Size: 24,
	// })
	// dc.SetFontFace(fontFace)

	// dc.SetHexColor("#00FF00")
	// dc.DrawString("Hello, world!", 500, 100)

	if err := drawImageHeading(dc, "Leeks Dashboard", dashboardData.DateString); err != nil {
		return nil, err
	}
	if err := drawLeafInfo(dc, dashboardData.LeafData); err != nil {
		return nil, err
	}
	if err := drawWeatherInfo(dc, dashboardData.WeatherData, 130, 30); err != nil {
		return nil, err
	}
	if err := drawPistat(dc, dashboardData.Pistat0, 275, 330); err != nil {
		return nil, err
	}
	if err := drawMessage(dc, dashboardData.Message); err != nil {
		return nil, err
	}
	if err := drawActions(dc, dashboardData.Actions); err != nil {
		return nil, err
	}
	return dc, nil
}

func drawImageHeading(dc *gg.Context, text string, dateText string) error {
	dc.SetHexColor("#000000")

	if err := dc.LoadFontFace("fonts/FiraCode-Regular.ttf", 17.5); err != nil {
		return fmt.Errorf("failed to load font: %w", err)
	}
	drawStringCentered(dc, text, float64(dc.Width())/4, 10)

	if err := dc.LoadFontFace("fonts/FiraCode-Regular.ttf", 25); err != nil {
		return fmt.Errorf("failed to load font: %w", err)
	}
	w, h := dc.MeasureString(dateText)
	headingX := float64(dc.Width()) - w - 10
	dc.DrawString(dateText, headingX, 10+h)

	return nil
}

func drawLeafInfo(dc *gg.Context, leafData *data.LeafData) error {

	if leafData == nil {
		return nil
	}

	dc.SetHexColor("#000000")

	if err := dc.LoadFontFace("fonts/FiraCode-Regular.ttf", 30); err != nil {
		return err
	}
	text := fmt.Sprintf("Range: %0.0f miles", leafData.CruisingRangeAcOffMiles)
	_, h := dc.MeasureString(text)
	dc.DrawString(text, 110, 50+h)

	if err := dc.LoadFontFace("fonts/FiraCode-Regular.ttf", 17.5); err != nil {
		return err
	}
	text = fmt.Sprintf("(%0.0f with climate control)", leafData.CruisingRangeAcOnMiles)
	_, h = dc.MeasureString(text)
	dc.DrawString(text, 110, 90+h)

	destImage, err := loadAndResizePng(path.Join("leaf_images", leafData.IconPath), 70, 70, 1)
	if err != nil {
		return err
	}
	dc.DrawImage(destImage, 10, 40)

	return nil
}

func drawWeatherInfo(dc *gg.Context, weatherData *data.WeatherData, top float64, left float64) error {

	if weatherData == nil {
		return nil
	}

	dc.SetHexColor("#000000")

	weatherWidth := float64(250)
	weatherOffsetX := float64(50)

	iconSize := 150
	iconOffsetY := -5
	timeFontSize := float64(20)
	tempMainFontSize := float64(30)
	tempOffsetY := float64(40)
	tempFeelsFontSize := float64(20)
	tempFeelsOffsetY := float64(35)
	descriptionFontSize := float64(20)
	descriptionOffsetY := float64(50)
	windOffsetY := float64(25)

	weatherItems := append([]data.WeatherDataPoint{weatherData.Current}, weatherData.Forecast[:2]...)
	for _, weatherItem := range weatherItems {
		currentTop := top

		// Draw icon
		icon, err := loadAndResizePng(weatherItem.IconPath, iconSize, iconSize, 0.7)
		if err != nil {
			return fmt.Errorf("failed to load icon (%q): %w", weatherItem.IconPath, err)
		}
		dc.DrawImage(icon, int(left), int(currentTop)+iconOffsetY)

		// Draw time
		if err := dc.LoadFontFace("fonts/FiraCode-Regular.ttf", timeFontSize); err != nil {
			return fmt.Errorf("failed to load font: %w", err)
		}
		drawStringCentered(dc, weatherItem.Time, left+weatherWidth/2, currentTop)

		// Draw main temp
		currentTop += tempOffsetY
		if err := dc.LoadFontFace("fonts/FiraCode-Regular.ttf", tempMainFontSize); err != nil {
			return fmt.Errorf("failed to load font: %w", err)
		}
		drawStringLeft(dc, fmt.Sprintf("%0.0f°C", weatherItem.Temperature), left+float64(iconSize), currentTop)

		// Draw feels like temp
		currentTop += tempFeelsOffsetY
		if err := dc.LoadFontFace("fonts/FiraCode-Regular.ttf", tempFeelsFontSize); err != nil {
			return fmt.Errorf("failed to load font: %w", err)
		}
		drawStringLeft(dc, fmt.Sprintf("%0.0f°C, %0.0f%%", weatherItem.FeelsLike, weatherItem.Humidity), left+float64(iconSize), currentTop)

		// Draw description + wind
		if err := dc.LoadFontFace("fonts/FiraCode-Regular.ttf", descriptionFontSize); err != nil {
			return fmt.Errorf("failed to load font: %w", err)
		}
		currentTop += descriptionOffsetY
		drawStringCentered(dc, weatherItem.Description, left+weatherWidth/2, currentTop)
		currentTop += windOffsetY
		drawStringCentered(dc,
			fmt.Sprintf("%s mph (%s mph gusts)", speedOrNA(weatherItem.WindSpeedMph), speedOrNA(weatherItem.WindGustMph)),
			left+weatherWidth/2,
			currentTop)

		// update position for next weather item
		left += weatherWidth + weatherOffsetX

		// Update sizes for subsequent items
		weatherWidth = 200
		iconSize = 85
		iconOffsetY = 5
		timeFontSize = 17
		tempMainFontSize = 25
		tempOffsetY = 25
		tempFeelsFontSize = 17.5
		tempFeelsOffsetY = 35
		descriptionFontSize = 15
		descriptionOffsetY = 30
		weatherOffsetX = 10
		windOffsetY = 20

	}

	_ = tempMainFontSize
	_ = tempFeelsFontSize
	_ = descriptionFontSize

	return nil
}

func drawPistat(dc *gg.Context, pistatData *data.Temperature, top int, left int) error {
	if pistatData == nil {
		return nil
	}

	dc.SetHexColor("#000000")
	if err := dc.LoadFontFace("fonts/FiraCode-Regular.ttf", 15); err != nil {
		return fmt.Errorf("failed to load font: %w", err)
	}

	drawStringLeft(
		dc,
		fmt.Sprintf("pistat-0: %0.1f°C (%0.1f%%)", pistatData.Temperature, pistatData.Humidity),
		float64(left),
		float64(top),
	)

	return nil
}

func drawMessage(dc *gg.Context, message string) error {
	if message == "" {
		return nil
	}

	dc.SetHexColor("#000000")

	messageFontSize := 25
	for messageFontSize > 10 {
		if err := dc.LoadFontFace("fonts/FiraCode-Regular.ttf", float64(messageFontSize)); err != nil {
			return fmt.Errorf("failed to load font: %w", err)
		}
		w, _ := dc.MeasureString(message)
		if w < float64(dc.Width())-20 {
			break
		}
		messageFontSize -= 1
	}
	drawStringCentered(dc, message, float64(dc.Width())/2, float64(400))

	return nil
}
func drawActions(dc *gg.Context, actions []data.Action) error {
	dc.SetHexColor("#000000")

	if err := dc.LoadFontFace("fonts/FiraCode-Regular.ttf", 15); err != nil {
		return fmt.Errorf("failed to load font: %w", err)
	}
	buttonPositions := []float64{80, 240, 400, 560, 720}
	for i, x := range buttonPositions {
		dc.SetLineWidth(1)
		dc.DrawLine(x, 460, x, 490)
		dc.Stroke()

		if i < len(actions) {
			drawStringCentered(dc, actions[i].DisplayName, x+5, 440)
		}
	}

	return nil
}

func speedOrNA(speed *float32) string {
	if speed == nil {
		return "n/a"
	}
	return fmt.Sprintf("%0.0f", *speed)
}
func drawStringCentered(dc *gg.Context, text string, x, y float64) {
	w, h := dc.MeasureString(text)
	dc.DrawString(text, x-w/2, y+h)
}
func drawStringLeft(dc *gg.Context, text string, x, y float64) {
	_, h := dc.MeasureString(text)
	dc.DrawString(text, x, y+h)
}

func loadAndResizePng(imagePath string, width int, height int, darkenFactor float64) (*image.RGBA, error) {
	imageFile, err := os.Open(imagePath)
	if err != nil {
		return nil, err
	}
	defer imageFile.Close()

	// Decode the image (from PNG to image.Image):
	sourceImage, err := png.Decode(imageFile)
	if err != nil {
		return nil, err
	}

	// Set the expected size that you want:
	destImage := image.NewRGBA(image.Rect(0, 0, width, height))

	// Resize:
	draw.BiLinear.Scale(destImage, destImage.Rect, sourceImage, sourceImage.Bounds(), draw.Over, nil)

	if darkenFactor != 1 {
		bounds := destImage.Bounds()
		for x := bounds.Min.X; x < bounds.Max.X; x++ {
			for y := bounds.Min.Y; y < bounds.Max.Y; y++ {
				r, g, b, a := destImage.At(x, y).RGBA()
				darkenedColor := color.RGBA{
					R: uint8(float64(r>>8) * darkenFactor),
					G: uint8(float64(g>>8) * darkenFactor),
					B: uint8(float64(b>>8) * darkenFactor),
					A: uint8(a >> 8),
				}
				destImage.Set(x, y, darkenedColor)
			}
		}
	}
	return destImage, nil
}
