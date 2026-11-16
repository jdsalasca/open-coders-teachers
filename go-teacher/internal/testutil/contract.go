// Package testutil contiene contratos reutilizables por los adaptadores.
package testutil

import (
	"context"
	"testing"

	"teachers/goteacher/internal/domain"
)

// RepositoryContract verifica el comportamiento minimo de un RepositoryPort.
func RepositoryContract(t *testing.T, repo domain.RepositoryPort) {
	t.Helper()
	ctx := context.Background()

	first, err := repo.Add(ctx, "uno")
	if err != nil {
		t.Fatalf("agregar fallo: %v", err)
	}
	second, err := repo.Add(ctx, "dos")
	if err != nil {
		t.Fatalf("agregar fallo: %v", err)
	}
	if first.ID == second.ID {
		t.Fatalf("ids repetidos: %d", first.ID)
	}

	all, err := repo.All(ctx)
	if err != nil {
		t.Fatalf("listar fallo: %v", err)
	}
	if len(all) != 2 {
		t.Fatalf("quiero 2 tareas, hay %d", len(all))
	}
}
