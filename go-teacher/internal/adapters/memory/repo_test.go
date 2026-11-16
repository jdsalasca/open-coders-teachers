package memory_test

import (
	"testing"

	"teachers/goteacher/internal/adapters/memory"
	"teachers/goteacher/internal/domain"
	"teachers/goteacher/internal/testutil"
)

func TestRepositoryCumpleContrato(t *testing.T) {
	testutil.RepositoryContract(t, &memory.Repository{})
}

func TestAllDevuelveCopia(t *testing.T) {
	repo := &memory.Repository{}
	repo.Save(domain.Task{ID: 1, Title: "uno"})

	repo.All()[0].Title = "mutado"

	if repo.All()[0].Title != "uno" {
		t.Fatal("All debe devolver una copia")
	}
}
