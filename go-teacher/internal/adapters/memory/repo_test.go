package memory_test

import (
	"context"
	"errors"
	"sync"
	"testing"

	"teachers/goteacher/internal/adapters/memory"
	"teachers/goteacher/internal/domain"
	"teachers/goteacher/internal/testutil"
)

func TestRepositoryCumpleContrato(t *testing.T) {
	testutil.RepositoryContract(t, &memory.Repository{})
}

func TestListDevuelveCopia(t *testing.T) {
	ctx := context.Background()
	repo := &memory.Repository{}
	if _, err := repo.Create(ctx, "uno", ""); err != nil {
		t.Fatal(err)
	}
	page, err := domain.NewPage(10, 0)
	if err != nil {
		t.Fatal(err)
	}

	tasks, err := repo.List(ctx, page)
	if err != nil {
		t.Fatal(err)
	}
	tasks[0] = domain.Task{}

	again, err := repo.List(ctx, page)
	if err != nil {
		t.Fatal(err)
	}
	if again[0].Title() != "uno" {
		t.Fatal("List debe devolver una copia")
	}
}

func TestCreateRespetaContextoCancelado(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	repo := &memory.Repository{}

	_, err := repo.Create(ctx, "uno", "")

	if !errors.Is(err, context.Canceled) {
		t.Fatalf("err = %v, quiero context.Canceled", err)
	}
}

func TestCreateEsIdempotenteEnConcurrente(t *testing.T) {
	repo := &memory.Repository{}

	ids := createConcurrent(t, repo, 20, "misma-clave")

	first := ids[0]
	for _, id := range ids[1:] {
		if id != first {
			t.Fatalf("id = %d, quiero %d para la misma clave", id, first)
		}
	}
	page, err := domain.NewPage(10, 0)
	if err != nil {
		t.Fatal(err)
	}
	tasks, err := repo.List(context.Background(), page)
	if err != nil {
		t.Fatal(err)
	}
	if len(tasks) != 1 {
		t.Fatalf("quiero 1 tarea, hay %d", len(tasks))
	}
}

func TestCreateEsSeguroEnConcurrente(t *testing.T) {
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
	repo := &memory.Repository{}

	ids := createConcurrent(t, repo, count, "")
	assertStored(t, repo, count)
	return ids
}

func createConcurrent(t *testing.T, repo *memory.Repository, count int, key string) []int {
	t.Helper()
	ctx := context.Background()
	var wg sync.WaitGroup
	ids := make(chan int, count)

	for range count {
		wg.Go(func() {
			result, err := repo.Create(ctx, "tarea", key)
			if err != nil {
				t.Errorf("Create fallo: %v", err)
				return
			}
			ids <- result.Task.ID()
		})
	}
	wg.Wait()
	close(ids)

	out := make([]int, 0, count)
	for id := range ids {
		out = append(out, id)
	}
	return out
}

func assertStored(t *testing.T, repo *memory.Repository, count int) {
	t.Helper()
	page, err := domain.NewPage(domain.MaxPageSize, 0)
	if err != nil {
		t.Fatal(err)
	}
	all, err := repo.List(context.Background(), page)
	if err != nil {
		t.Fatal(err)
	}
	if len(all) != count {
		t.Fatalf("quiero %d tareas, hay %d", count, len(all))
	}
	for _, task := range all {
		if task.Title() == "" {
			t.Fatal("hay una tarea con titulo vacio")
		}
	}
}
