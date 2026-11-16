package app_test

import (
	"context"
	"errors"
	"strings"
	"testing"
	"testing/quick"

	"teachers/goteacher/internal/app"
	"teachers/goteacher/internal/domain"
)

type fakeRepo struct {
	tasks  []domain.Task
	addErr error
	allErr error
}

// Add asigna un id incremental.
func (f *fakeRepo) Add(ctx context.Context, title string) (domain.Task, error) {
	if err := ctx.Err(); err != nil {
		return domain.Task{}, err
	}
	if f.addErr != nil {
		return domain.Task{}, f.addErr
	}
	task, err := domain.NewTask(len(f.tasks)+1, title)
	if err != nil {
		return domain.Task{}, err
	}
	f.tasks = append(f.tasks, task)
	return task, nil
}

// All devuelve lo guardado.
func (f *fakeRepo) All(ctx context.Context) ([]domain.Task, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if f.allErr != nil {
		return nil, f.allErr
	}
	return f.tasks, nil
}

func TestAddGuardaLaTarea(t *testing.T) {
	service := app.NewService(&fakeRepo{})

	task, err := service.Add(context.Background(), "estudiar")
	if err != nil {
		t.Fatal(err)
	}

	if task.ID != 1 {
		t.Fatalf("id = %d, quiero 1", task.ID)
	}
	tasks, err := service.List(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if len(tasks) != 1 {
		t.Fatalf("quiero 1 tarea, hay %d", len(tasks))
	}
}

func TestAddRechazaTituloVacio(t *testing.T) {
	service := app.NewService(&fakeRepo{})

	_, err := service.Add(context.Background(), "   ")

	if !errors.Is(err, domain.ErrEmptyTitle) {
		t.Fatalf("err = %v, quiero ErrEmptyTitle", err)
	}
}

func TestAddPropagaErrorDelRepositorio(t *testing.T) {
	service := app.NewService(&fakeRepo{addErr: errors.New("base caida")})

	_, err := service.Add(context.Background(), "estudiar")

	if err == nil {
		t.Fatal("quiero error del repositorio")
	}
}

func TestAddRespetaContextoCancelado(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	service := app.NewService(&fakeRepo{})

	_, err := service.Add(ctx, "estudiar")

	if !errors.Is(err, context.Canceled) {
		t.Fatalf("err = %v, quiero context.Canceled", err)
	}
}

func TestAddConservaTitulo(t *testing.T) {
	f := func(title string) bool {
		if strings.TrimSpace(title) == "" {
			return true
		}
		service := app.NewService(&fakeRepo{})
		task, err := service.Add(context.Background(), title)
		return err == nil && task.Title == title
	}
	if err := quick.Check(f, nil); err != nil {
		t.Fatal(err)
	}
}
