// Package testutil contiene contratos reutilizables por los adaptadores.
package testutil

import (
	"context"
	"errors"
	"testing"

	"teachers/goteacher/internal/domain"
)

// RepositoryContract verifica ids, idempotencia, orden y paginacion.
func RepositoryContract(t *testing.T, repo domain.RepositoryPort) {
	t.Helper()
	page, err := domain.NewPage(10, 0)
	if err != nil {
		t.Fatal(err)
	}

	first := createNew(t, repo, "uno", "clave-1")
	second := createNew(t, repo, "dos", "clave-2")
	if first.ID() == second.ID() {
		t.Fatalf("ids repetidos: %d", first.ID())
	}

	assertReplay(t, repo, first)
	assertList(t, repo, page, []domain.Task{first, second})
	assertPage(t, repo, second)
	assertInvalidPage(t, repo)
}

func assertInvalidPage(t *testing.T, repo domain.RepositoryPort) {
	t.Helper()
	_, err := repo.List(context.Background(), domain.Page{Limit: 0})
	if !errors.Is(err, domain.ErrInvalidPage) {
		t.Fatalf("err = %v, quiero ErrInvalidPage", err)
	}
}

func createNew(
	t *testing.T,
	repo domain.RepositoryPort,
	title string,
	key string,
) domain.Task {
	t.Helper()
	result, err := repo.Create(context.Background(), title, key)
	if err != nil {
		t.Fatalf("crear fallo: %v", err)
	}
	if !result.Created {
		t.Fatalf("la creacion de %q debe ser nueva", title)
	}
	return result.Task
}

func assertReplay(t *testing.T, repo domain.RepositoryPort, original domain.Task) {
	t.Helper()
	replay, err := repo.Create(context.Background(), "ignorado", "clave-1")
	if err != nil {
		t.Fatalf("replay fallo: %v", err)
	}
	if replay.Created {
		t.Fatal("la clave repetida no debe crear otra tarea")
	}
	if replay.Task.ID() != original.ID() || replay.Task.Title() != original.Title() {
		t.Fatalf("replay = %+v, quiero la tarea original", replay.Task)
	}
}

func assertList(
	t *testing.T,
	repo domain.RepositoryPort,
	page domain.Page,
	expected []domain.Task,
) {
	t.Helper()
	tasks, err := repo.List(context.Background(), page)
	if err != nil {
		t.Fatalf("listar fallo: %v", err)
	}
	if len(tasks) != len(expected) {
		t.Fatalf("quiero %d tareas, hay %d", len(expected), len(tasks))
	}
	for index, task := range tasks {
		if task.ID() != expected[index].ID() {
			t.Fatal("List debe ordenar por id")
		}
	}
}

func assertPage(t *testing.T, repo domain.RepositoryPort, second domain.Task) {
	t.Helper()
	one, err := domain.NewPage(1, 1)
	if err != nil {
		t.Fatal(err)
	}
	paged, err := repo.List(context.Background(), one)
	if err != nil {
		t.Fatalf("paginar fallo: %v", err)
	}
	if len(paged) != 1 || paged[0].ID() != second.ID() {
		t.Fatalf("pagina = %+v, quiero la segunda tarea", paged)
	}
}
