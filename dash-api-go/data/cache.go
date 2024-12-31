package data

import (
	"sync"
	"time"
)

type CacheItem[T any] struct {
	Value     *T
	ExpiresAt time.Time
}
type Cache[K comparable, V any] struct {
	items map[K]*CacheItem[V]
	ttl   time.Duration
	mutex sync.Mutex
}

// NewCache creates a new cache.
func NewCache[K comparable, V any](ttl time.Duration) *Cache[K, V] {
	return &Cache[K, V]{
		items: make(map[K]*CacheItem[V]),
		ttl:   ttl,
		mutex: sync.Mutex{},
	}
}

// Get returns the value associated with the key and a boolean indicating whether the key was found.
// Getting an item extends its TTL
func (c *Cache[K, V]) Get(key K) *V {
	c.mutex.Lock()
	defer c.mutex.Unlock()

	item, found := c.items[key]
	if !found {
		return nil
	}
	if time.Now().UTC().After(item.ExpiresAt) {
		delete(c.items, key)
		return nil
	}
	// update TTL
	item.ExpiresAt = time.Now().UTC().Add(c.ttl)

	return item.Value
}

// Set sets the value associated with the key and the expiration time.
func (c *Cache[K, V]) Set(key K, value *V) {
	c.mutex.Lock()
	defer c.mutex.Unlock()

	expiresAt := time.Now().UTC().Add(c.ttl)

	c.items[key] = &CacheItem[V]{
		Value:     value,
		ExpiresAt: expiresAt,
	}
}
