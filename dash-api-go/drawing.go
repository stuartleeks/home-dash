package main

import (
	"fmt"
	"image"
	"image/color"
	"image/png"
	"os"
	"path"

	"github.com/fogleman/gg"
	"github.com/stuartleeks/home-dash/dash-api/data"
	"golang.org/x/image/draw"
)

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
