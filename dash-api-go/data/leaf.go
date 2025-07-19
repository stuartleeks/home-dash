package data

import (
	"fmt"
	"time"
)

type UpdateDate time.Time

const updatedAtFormat = "2006-01-02 15:04:05"

func (u *UpdateDate) UnmarshalJSON(b []byte) error {
	if len(b) < 2 || b[0] != '"' || b[len(b)-1] != '"' {
		return fmt.Errorf("invalid time format: %s", b)
	}
	b = b[1 : len(b)-1]
	t, err := time.Parse(updatedAtFormat, string(b))
	if err != nil {
		return err
	}
	*u = UpdateDate(t)
	return nil
}
func (u UpdateDate) MarshalJSON() ([]byte, error) {
	return []byte(`"` + time.Time(u).Format(updatedAtFormat) + `"`), nil
}

type LeafData struct {
	UpdateDate              UpdateDate `json:"update_date"`
	IsConnected             bool       `json:"is_connected"`
	ChargingStatus          string     `json:"charging_status"`
	CruisingRangeAcOffMiles float32    `json:"cruising_range_ac_off_miles"`
	CruisingRangeAcOnMiles  float32    `json:"cruising_range_ac_on_miles"`
	IconPath                string     `json:"icon_path"`
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
