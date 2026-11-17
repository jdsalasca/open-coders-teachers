package sqlite_test

import (
	"context"
	"errors"
	"path/filepath"
	"sync"
	"testing"

	"teachers/goteacher/internal/adapters/sqlite"
	"teachers/goteacher/internal/domain"
	"teachers/goteacher/internal/testutil"
)

func openRepository(t *testing.T) *sqlite.Repository {
	t.Helper()
	return openAt(t, filepath.Join(t.TempDir(), "tasks.db"))
}

func openAt(t *testing.T, path string) *sqlite.Repository {
	t.Helper()
	repo, err := sqlite.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := repo.Close(); err != nil {
			t.Errorf("cerrar: %v", err)
		}
	})
	return repo
}

func page(t *testing.T) domain.Page {
	t.Helper()
	value, err := domain.NewPage(10, 0)
	if err != nil {
		t.Fatal(err)
	}
	return value
}

func TestRepositoryCumpleContrato(t *testing.T) {
	testutil.RepositoryContract(t, openRepository(t))
}

func TestPersisteEntreReinicios(t *testing.T) {
	path := filepath.Join(t.TempDir(), "tasks.db")

	created := createAndClose(t, path)
	reopened := openAt(t, path)

	assertPersisted(t, reopened)
	assertReplayPersisted(t, reopened, created)
}

func createAndClose(t *testing.T, path string) domain.Task {
	t.Helper()
	repo, err := sqlite.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	result, err := repo.Create(context.Background(), "uno", "clave")
	if err != nil {
		t.Fatal(err)
	}
	if err := repo.Close(); err != nil {
		t.Fatal(err)
	}
	return result.Task
}

func assertPersisted(t *testing.T, repo *sqlite.Repository) {
	t.Helper()
	tasks, err := repo.List(context.Background(), page(t))
	if err != nil {
		t.Fatal(err)
	}
	if len(tasks) != 1 || tasks[0].Title() != "uno" {
		t.Fatalf("tareas = %+v", tasks)
	}
}

func assertReplayPersisted(t *testing.T, repo *sqlite.Repository, created domain.Task) {
	t.Helper()
	replay, err := repo.Create(context.Background(), "otro", "clave")
	if err != nil {
		t.Fatal(err)
	}
	if replay.Created || replay.Task.ID() != created.ID() {
		t.Fatalf("replay = %+v, quiero la tarea original", replay)
	}
}

func TestRechazaTituloInvalido(t *testing.T) {
	ctx := context.Background()
	repo := openRepository(t)

	_, err := repo.Create(ctx, "   ", "")

	if !errors.Is(err, domain.ErrEmptyTitle) {
		t.Fatalf("err = %v, quiero ErrEmptyTitle", err)
	}
	tasks, err := repo.List(ctx, page(t))
	if err != nil {
		t.Fatal(err)
	}
	if len(tasks) != 0 {
		t.Fatalf("quiero 0 tareas, hay %d", len(tasks))
	}
}

func TestCreateConcurrenteConLaMismaClave(t *testing.T) {
	repo := openRepository(t)

	ids := createConcurrent(t, repo, 10, "misma-clave")

	assertSameIDs(t, ids)
	tasks, err := repo.List(context.Background(), page(t))
	if err != nil {
		t.Fatal(err)
	}
	if len(tasks) != 1 {
		t.Fatalf("quiero 1 tarea, hay %d", len(tasks))
	}
}

func TestIdempotenciaEntreDosInstancias(t *testing.T) {
	path := filepath.Join(t.TempDir(), "tasks.db")
	first := openAt(t, path)
	second := openAt(t, path)

	type outcome struct {
		result domain.CreateResult
		err    error
	}
	results := make(chan outcome, 2)
	for _, repo := range []*sqlite.Repository{first, second} {
		go func(repo *sqlite.Repository) {
			result, err := repo.Create(context.Background(), "tarea", "clave")
			results <- outcome{result: result, err: err}
		}(repo)
	}

	one := <-results
	two := <-results
	if one.err != nil || two.err != nil {
		t.Fatalf("errores: %v / %v", one.err, two.err)
	}
	if one.result.Task.ID() != two.result.Task.ID() {
		t.Fatalf("ids = %d / %d", one.result.Task.ID(), two.result.Task.ID())
	}
	if one.result.Created == two.result.Created {
		t.Fatal("uno debe crear y el otro hacer replay")
	}
	tasks, err := first.List(context.Background(), page(t))
	if err != nil {
		t.Fatal(err)
	}
	if len(tasks) != 1 {
		t.Fatalf("quiero 1 tarea, hay %d", len(tasks))
	}
}

func createConcurrent(
	t *testing.T,
	repo *sqlite.Repository,
	count int,
	key string,
) []int {
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

func assertSameIDs(t *testing.T, ids []int) {
	t.Helper()
	first := ids[0]
	for _, id := range ids[1:] {
		if id != first {
			t.Fatalf("id = %d, quiero %d para la misma clave", id, first)
		}
	}
}
