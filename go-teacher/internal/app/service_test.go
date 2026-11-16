package app_test

import (
	"testing"
	"testing/quick"

	"teachers/goteacher/internal/app"
	"teachers/goteacher/internal/domain"
)

type fakeRepo struct {
	tasks []domain.Task
}

// Save guarda en memoria.
func (f *fakeRepo) Save(task domain.Task) {
	f.tasks = append(f.tasks, task)
}

// All devuelve lo guardado.
func (f *fakeRepo) All() []domain.Task {
	return f.tasks
}

func TestAddGuardaLaTarea(t *testing.T) {
	service := app.NewService(&fakeRepo{})
	task := service.Add("estudiar")

	if task.ID != 1 {
		t.Fatalf("id = %d, quiero 1", task.ID)
	}
	if len(service.List()) != 1 {
		t.Fatalf("quiero 1 tarea, hay %d", len(service.List()))
	}
}

func TestAddConservaTitulo(t *testing.T) {
	f := func(title string) bool {
		service := app.NewService(&fakeRepo{})
		return service.Add(title).Title == title
	}
	if err := quick.Check(f, nil); err != nil {
		t.Fatal(err)
	}
}

func TestAddIncrementaElID(t *testing.T) {
	service := app.NewService(&fakeRepo{})
	service.Add("uno")
	second := service.Add("dos")

	if second.ID != 2 {
		t.Fatalf("id = %d, quiero 2", second.ID)
	}
}
