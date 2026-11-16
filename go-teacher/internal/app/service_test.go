package app_test

import (
	"errors"
	"strings"
	"testing"
	"testing/quick"

	"teachers/goteacher/internal/app"
	"teachers/goteacher/internal/domain"
)

type fakeRepo struct {
	tasks   []domain.Task
	saveErr error
	allErr  error
}

// Save guarda en memoria.
func (f *fakeRepo) Save(task domain.Task) error {
	if f.saveErr != nil {
		return f.saveErr
	}
	f.tasks = append(f.tasks, task)
	return nil
}

// All devuelve lo guardado.
func (f *fakeRepo) All() ([]domain.Task, error) {
	if f.allErr != nil {
		return nil, f.allErr
	}
	return f.tasks, nil
}

func TestAddGuardaLaTarea(t *testing.T) {
	service := app.NewService(&fakeRepo{})
	task, err := service.Add("estudiar")
	if err != nil {
		t.Fatal(err)
	}

	if task.ID != 1 {
		t.Fatalf("id = %d, quiero 1", task.ID)
	}
	tasks, err := service.List()
	if err != nil {
		t.Fatal(err)
	}
	if len(tasks) != 1 {
		t.Fatalf("quiero 1 tarea, hay %d", len(tasks))
	}
}

func TestAddUsaMaxMasUno(t *testing.T) {
	repo := &fakeRepo{tasks: []domain.Task{{ID: 1, Title: "uno"}, {ID: 3, Title: "tres"}}}
	service := app.NewService(repo)

	task, err := service.Add("cuatro")
	if err != nil {
		t.Fatal(err)
	}

	if task.ID != 4 {
		t.Fatalf("id = %d, quiero 4", task.ID)
	}
}

func TestAddRechazaTituloVacio(t *testing.T) {
	service := app.NewService(&fakeRepo{})

	_, err := service.Add("   ")

	if !errors.Is(err, app.ErrEmptyTitle) {
		t.Fatalf("err = %v, quiero ErrEmptyTitle", err)
	}
}

func TestAddPropagaErrorDelRepositorio(t *testing.T) {
	service := app.NewService(&fakeRepo{allErr: errors.New("base caida")})

	_, err := service.Add("estudiar")

	if err == nil {
		t.Fatal("quiero error del repositorio")
	}
}

func TestAddConservaTitulo(t *testing.T) {
	f := func(title string) bool {
		if strings.TrimSpace(title) == "" {
			return true
		}
		service := app.NewService(&fakeRepo{})
		task, err := service.Add(title)
		return err == nil && task.Title == title
	}
	if err := quick.Check(f, nil); err != nil {
		t.Fatal(err)
	}
}
