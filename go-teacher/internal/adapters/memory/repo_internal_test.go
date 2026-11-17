package memory

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"teachers/goteacher/internal/domain"
)

// probeContext avisa cuando el codigo comprueba el contexto por primera vez.
type probeContext struct {
	once      sync.Once
	firstCall chan struct{}
	cancelled atomic.Bool
}

func newProbeContext() *probeContext {
	return &probeContext{firstCall: make(chan struct{})}
}

func (c *probeContext) Deadline() (time.Time, bool) { return time.Time{}, false }

func (c *probeContext) Done() <-chan struct{} { return nil }

func (c *probeContext) Value(any) any { return nil }

func (c *probeContext) Err() error {
	c.once.Do(func() { close(c.firstCall) })
	if c.cancelled.Load() {
		return context.Canceled
	}
	return nil
}

func assertCancelWhileWaiting(
	t *testing.T,
	repo *Repository,
	call func(context.Context) error,
) {
	t.Helper()
	probe := newProbeContext()
	done := make(chan error, 1)
	page, err := domain.NewPage(10, 0)
	if err != nil {
		t.Fatal(err)
	}

	repo.mu.Lock()
	go func() { done <- call(probe) }()
	<-probe.firstCall
	probe.cancelled.Store(true)
	repo.mu.Unlock()

	if err := <-done; !errors.Is(err, context.Canceled) {
		t.Fatalf("err = %v, quiero context.Canceled", err)
	}
	if tasks, err := repo.List(context.Background(), page); err != nil || len(tasks) != 0 {
		t.Fatalf("no debe mutar: tasks=%v err=%v", tasks, err)
	}
}

func TestCreateDetectaCancelacionMientrasEsperaElMutex(t *testing.T) {
	repo := &Repository{}

	assertCancelWhileWaiting(t, repo, func(ctx context.Context) error {
		_, err := repo.Create(ctx, "tarea", "")
		return err
	})
}

func TestListDetectaCancelacionMientrasEsperaElMutex(t *testing.T) {
	repo := &Repository{}

	assertCancelWhileWaiting(t, repo, func(ctx context.Context) error {
		_, err := repo.List(ctx, domain.Page{Limit: 10})
		return err
	})
}
