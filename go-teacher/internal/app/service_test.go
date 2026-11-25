package app_test

import (
	"context"
	"errors"
	"strings"
	"testing"
	"testing/quick"
	"unicode/utf8"

	"teachers/goteacher/internal/app"
	"teachers/goteacher/internal/domain"
)

type fakeRepo struct {
	tasks  []domain.Task
	keys   map[string]domain.Task
	addErr error
	allErr error
}

// Create asigna un id incremental y respeta la clave de idempotencia.
func (f *fakeRepo) Create(
	ctx context.Context,
	title string,
	key string,
) (domain.CreateResult, error) {
	if err := ctx.Err(); err != nil {
		return domain.CreateResult{}, err
	}
	if f.addErr != nil {
		return domain.CreateResult{}, f.addErr
	}
	if task, ok := f.keys[key]; ok && key != "" {
		return domain.CreateResult{Task: task, Created: false}, nil
	}
	task, err := domain.NewTask(len(f.tasks)+1, title, false)
	if err != nil {
		return domain.CreateResult{}, err
	}
	f.tasks = append(f.tasks, task)
	if key != "" {
		if f.keys == nil {
			f.keys = make(map[string]domain.Task)
		}
		f.keys[key] = task
	}
	return domain.CreateResult{Task: task, Created: true}, nil
}

// List devuelve una pagina de lo guardado.
func (f *fakeRepo) List(ctx context.Context, page domain.Page) ([]domain.Task, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if f.allErr != nil {
		return nil, f.allErr
	}
	start := min(page.Offset, len(f.tasks))
	end := min(start+page.Limit, len(f.tasks))
	out := make([]domain.Task, end-start)
	copy(out, f.tasks[start:end])
	return out, nil
}

func page(t *testing.T, limit, offset int) domain.Page {
	t.Helper()
	value, err := domain.NewPage(limit, offset)
	if err != nil {
		t.Fatal(err)
	}
	return value
}

func TestAddGuardaLaTarea(t *testing.T) {
	service := app.NewService(&fakeRepo{})

	result, err := service.Add(context.Background(), "estudiar", "")
	if err != nil {
		t.Fatal(err)
	}

	if result.Task.ID() != 1 {
		t.Fatalf("id = %d, quiero 1", result.Task.ID())
	}
	if !result.Created {
		t.Fatal("Created = false, quiero true")
	}
	tasks, err := service.List(context.Background(), page(t, 10, 0))
	if err != nil {
		t.Fatal(err)
	}
	if len(tasks) != 1 {
		t.Fatalf("quiero 1 tarea, hay %d", len(tasks))
	}
}

func TestAddEsIdempotenteConLaMismaClave(t *testing.T) {
	service := app.NewService(&fakeRepo{})
	ctx := context.Background()

	first, err := service.Add(ctx, "estudiar", "clave")
	if err != nil {
		t.Fatal(err)
	}
	second, err := service.Add(ctx, "otro", "clave")
	if err != nil {
		t.Fatal(err)
	}

	if second.Created {
		t.Fatal("la clave repetida no debe crear otra tarea")
	}
	if second.Task.ID() != first.Task.ID() || second.Task.Title() != "estudiar" {
		t.Fatalf("replay = %+v, quiero la tarea original", second.Task)
	}
}

func TestAddRechazaTituloVacio(t *testing.T) {
	service := app.NewService(&fakeRepo{})

	_, err := service.Add(context.Background(), "   ", "")

	if !errors.Is(err, domain.ErrEmptyTitle) {
		t.Fatalf("err = %v, quiero ErrEmptyTitle", err)
	}
}

func TestAddRechazaTituloLargo(t *testing.T) {
	service := app.NewService(&fakeRepo{})

	_, err := service.Add(context.Background(), strings.Repeat("😀", domain.MaxTitleLength+1), "")

	if !errors.Is(err, domain.ErrTitleTooLong) {
		t.Fatalf("err = %v, quiero ErrTitleTooLong", err)
	}
}

func TestAddPropagaErrorDelRepositorio(t *testing.T) {
	service := app.NewService(&fakeRepo{addErr: errors.New("base caida")})

	_, err := service.Add(context.Background(), "estudiar", "")

	if err == nil {
		t.Fatal("quiero error del repositorio")
	}
}

func TestListPropagaErrorDelRepositorio(t *testing.T) {
	service := app.NewService(&fakeRepo{allErr: errors.New("base caida")})

	_, err := service.List(context.Background(), page(t, 10, 0))

	if err == nil {
		t.Fatal("quiero error del repositorio")
	}
}

func TestListRechazaPaginaInvalida(t *testing.T) {
	service := app.NewService(&fakeRepo{})

	_, err := service.List(context.Background(), domain.Page{Limit: 0, Offset: 0})

	if !errors.Is(err, domain.ErrInvalidPage) {
		t.Fatalf("err = %v, quiero ErrInvalidPage", err)
	}
}

func TestAddRespetaContextoCancelado(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	service := app.NewService(&fakeRepo{})

	_, err := service.Add(ctx, "estudiar", "")

	if !errors.Is(err, context.Canceled) {
		t.Fatalf("err = %v, quiero context.Canceled", err)
	}
}

func TestAddConservaTitulo(t *testing.T) {
	f := func(title string) bool {
		if strings.TrimSpace(title) == "" || utf8.RuneCountInString(title) > domain.MaxTitleLength {
			return true
		}
		service := app.NewService(&fakeRepo{})
		result, err := service.Add(context.Background(), title, "")
		return err == nil && result.Task.Title() == title
	}
	if err := quick.Check(f, nil); err != nil {
		t.Fatal(err)
	}
}
