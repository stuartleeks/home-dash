package data

type LeafData struct {
	IsConnected             bool    `json:"is_connected"`
	ChargingStatus          string  `json:"charging_status"`
	CruisingRangeAcOffMiles float32 `json:"cruising_range_ac_off_miles"`
	CruisingRangeAcOnMiles  float32 `json:"cruising_range_ac_on_miles"`
	IconPath                string  `json:"icon_path"`
}

const (
	LEAF_ICON_NOT_PLUGGED_IN = "not_plugged_in.png"
	LEAF_ICON_PLUGGED_IN     = "plugged_in.png"
	LEAF_ICON_CHARGING       = "charging.png"
)

func (leafData *LeafData) GetIconPath() string {
	if leafData.ChargingStatus != "NOT_CHARGING" {
		return LEAF_ICON_CHARGING
	} else if leafData.IsConnected {
		return LEAF_ICON_PLUGGED_IN
	} else {
		return LEAF_ICON_NOT_PLUGGED_IN
	}
}

func GetLeafData() (*LeafData, error) {
	leafData, err := JsonReadSharedLock[LeafData]("leaf-summary.json")
	if err != nil {
		return nil, err
	}
	leafData.IconPath = leafData.GetIconPath()
	return leafData, nil
}
