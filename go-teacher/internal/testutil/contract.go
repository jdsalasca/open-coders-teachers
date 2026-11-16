// Package testutil contiene contratos reutilizables por los adaptadores.
package testutil

import (
	"testing"

	"teachers/goteacher/internal/domain"
)

// RepositoryContract verifica el comportamiento minimo de un RepositoryPort.
func RepositoryContract(t *testing.T, repo domain.RepositoryPort) {
	t.Helper()

	repo.Save(domain.Task{ID: 1, Title: "uno"})
	all := repo.All()
	if len(all) != 1 || all[0].Title != "uno" {
		t.Fatalf("guardar no funciono: %+v", all)
	}

	repo.Save(domain.Task{ID: 1, Title: "dos"})
	all = repo.All()
	if len(all) != 1 || all[0].Title != "dos" {
		t.Fatalf("no reemplazo por id: %+v", all)
	}
}
