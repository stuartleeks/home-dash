package data

import (
	"encoding/json"
	"io"
	"os"
	"path"
	"syscall"

	"github.com/stuartleeks/home-dash/dash-api/config"
)

func getPath(filename string) string {
	if path.IsAbs(filename) {
		return filename
	}
	return path.Join(config.GetDashboardInfoPath(), filename)
}

func JsonReadSharedLock[T any](filename string) (*T, error) {
	dashboardInfoPath := getPath(filename)

	file, err := os.OpenFile(dashboardInfoPath, os.O_RDONLY, 0666)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	// lock the file (shared lock)
	if err = syscall.Flock(int(file.Fd()), syscall.LOCK_SH); err != nil {
		return nil, err
	}
	defer func() { _ = syscall.Flock(int(file.Fd()), syscall.LOCK_UN) }()

	var data T
	err = json.NewDecoder(file).Decode(&data)
	if err != nil {
		return nil, err
	}

	return &data, nil
}

func JsonUpdateExclusiveLock[T any](filename string, update func(data *T) error) error {
	dashboardInfoPath := getPath(filename)

	file, err := os.OpenFile(dashboardInfoPath, os.O_RDWR|os.O_CREATE, 0666)
	if err != nil {
		return err
	}
	defer file.Close()

	// lock the file (exlcusive lock)
	if err = syscall.Flock(int(file.Fd()), syscall.LOCK_EX); err != nil {
		return err
	}
	defer func() { _ = syscall.Flock(int(file.Fd()), syscall.LOCK_UN) }()

	var data T
	err = json.NewDecoder(file).Decode(&data)
	if err != nil {
		return err
	}

	if _, err := file.Seek(0, io.SeekStart); err != nil {
		return err
	}

	err = update(&data)
	if err != nil {
		return err
	}

	err = json.NewEncoder(file).Encode(data)

	if err != nil {
		return err
	}

	// Get the current position of the file pointer and truncate the file to that position
	pos, err := file.Seek(0, io.SeekCurrent)
	if err != nil {
		return err
	}
	err = file.Truncate(pos)

	return err
}
