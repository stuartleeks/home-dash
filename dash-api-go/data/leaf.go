package data

type LeafData struct {
	IsPluggedIn             bool    `json:"is_plugged_in"`
	IsCharging              bool    `json:"is_charging"`
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
	if leafData.IsCharging {
		return LEAF_ICON_CHARGING
	} else if leafData.IsPluggedIn {
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
