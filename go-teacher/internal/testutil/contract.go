// Package testutil contiene contratos reutilizables por los adaptadores.
package testutil

import (
	"testing"

	"teachers/goteacher/internal/domain"
)

// RepositoryContract verifica el comportamiento minimo de un RepositoryPort.
func RepositoryContract(t *testing.T, repo domain.RepositoryPort) {
	t.Helper()

	save := func(task domain.Task) {
		t.Helper()
		if err := repo.Save(task); err != nil {
			t.Fatalf("guardar fallo: %v", err)
		}
	}
	all := func() []domain.Task {
		t.Helper()
		tasks, err := repo.All()
		if err != nil {
			t.Fatalf("listar fallo: %v", err)
		}
		return tasks
	}

	save(domain.Task{ID: 1, Title: "uno"})
	assertSingle(t, all(), "uno")
	save(domain.Task{ID: 1, Title: "dos"})
	assertSingle(t, all(), "dos")
}

func assertSingle(t *testing.T, tasks []domain.Task, title string) {
	t.Helper()
	if len(tasks) != 1 || tasks[0].Title != title {
		t.Fatalf("quiero una tarea %q, hay %+v", title, tasks)
	}
}
