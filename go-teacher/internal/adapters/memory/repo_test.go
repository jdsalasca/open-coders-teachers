package memory_test

import (
	"context"
	"errors"
	"sync"
	"testing"

	"teachers/goteacher/internal/adapters/memory"
	"teachers/goteacher/internal/testutil"
)

func TestRepositoryCumpleContrato(t *testing.T) {
	testutil.RepositoryContract(t, &memory.Repository{})
}

func TestAllDevuelveCopia(t *testing.T) {
	ctx := context.Background()
	repo := &memory.Repository{}
	if _, err := repo.Add(ctx, "uno"); err != nil {
		t.Fatal(err)
	}

	tasks, err := repo.All(ctx)
	if err != nil {
		t.Fatal(err)
	}
	tasks[0].Title = "mutado"

	again, err := repo.All(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if again[0].Title != "uno" {
		t.Fatal("All debe devolver una copia")
	}
}

func TestAddRespetaContextoCancelado(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	repo := &memory.Repository{}

	_, err := repo.Add(ctx, "uno")

	if !errors.Is(err, context.Canceled) {
		t.Fatalf("err = %v, quiero context.Canceled", err)
	}
}

func TestAddEsSeguroEnConcurrente(t *testing.T) {
	ids := addConcurrent(t, 50)
	seen := map[int]bool{}
	for _, id := range ids {
		if seen[id] {
			t.Fatalf("id duplicado: %d", id)
		}
		seen[id] = true
	}
	if len(seen) != 50 {
		t.Fatalf("quiero 50 ids, hay %d", len(seen))
	}
}

func addConcurrent(t *testing.T, count int) []int {
	t.Helper()
	ctx := context.Background()
	repo := &memory.Repository{}
	var wg sync.WaitGroup
	ids := make(chan int, count)

	for range count {
		wg.Add(1)
		go func() {
			defer wg.Done()
			task, err := repo.Add(ctx, "tarea")
			if err != nil {
				t.Errorf("Add fallo: %v", err)
				return
			}
			ids <- task.ID
		}()
	}
	wg.Wait()
	close(ids)

	out := make([]int, 0, count)
	for id := range ids {
		out = append(out, id)
	}
	return out
}
