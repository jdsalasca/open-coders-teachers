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
	if err := repo.Save(domain.Task{ID: 1, Title: "uno"}); err != nil {
		t.Fatal(err)
	}

	tasks, err := repo.All()
	if err != nil {
		t.Fatal(err)
	}
	tasks[0].Title = "mutado"

	again, err := repo.All()
	if err != nil {
		t.Fatal(err)
	}
	if again[0].Title != "uno" {
		t.Fatal("All debe devolver una copia")
	}
}
