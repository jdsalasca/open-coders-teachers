package memory_test

import (
	"testing"

	"teachers/goteacher/internal/adapters/memory"
	"teachers/goteacher/internal/domain"
)

func TestSaveReemplazaPorID(t *testing.T) {
	repo := &memory.Repository{}
	repo.Save(domain.Task{ID: 1, Title: "uno"})
	repo.Save(domain.Task{ID: 1, Title: "dos"})

	tasks := repo.All()
	if len(tasks) != 1 {
		t.Fatalf("quiero 1 tarea, hay %d", len(tasks))
	}
	if tasks[0].Title != "dos" {
		t.Fatalf("title = %q, quiero dos", tasks[0].Title)
	}
}

func TestAllDevuelveCopia(t *testing.T) {
	repo := &memory.Repository{}
	repo.Save(domain.Task{ID: 1, Title: "uno"})

	repo.All()[0].Title = "mutado"

	if repo.All()[0].Title != "uno" {
		t.Fatal("All debe devolver una copia")
	}
}
