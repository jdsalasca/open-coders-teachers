package memory

import (
	"context"
	"errors"
	"testing"
)

func TestAddDetectaCancelacionMientrasEsperaElMutex(t *testing.T) {
	repo := &Repository{}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)

	repo.mu.Lock()
	go func() {
		_, err := repo.Add(ctx, "tarea")
		done <- err
	}()
	cancel()
	repo.mu.Unlock()

	if err := <-done; !errors.Is(err, context.Canceled) {
		t.Fatalf("err = %v, quiero context.Canceled", err)
	}
}

func TestAllDetectaCancelacionMientrasEsperaElMutex(t *testing.T) {
	repo := &Repository{}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)

	repo.mu.Lock()
	go func() {
		_, err := repo.All(ctx)
		done <- err
	}()
	cancel()
	repo.mu.Unlock()

	if err := <-done; !errors.Is(err, context.Canceled) {
		t.Fatalf("err = %v, quiero context.Canceled", err)
	}
}
