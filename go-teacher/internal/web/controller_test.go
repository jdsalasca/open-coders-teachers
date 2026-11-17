package web_test

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"testing"

	"teachers/goteacher/internal/adapters/memory"
	"teachers/goteacher/internal/app"
	"teachers/goteacher/internal/domain"
	"teachers/goteacher/internal/web"
)

var errRepository = errors.New("repositorio caido")

type failingRepository struct{}

func (failingRepository) Add(context.Context, string) (domain.Task, error) {
	return domain.Task{}, errRepository
}

func (failingRepository) All(context.Context) ([]domain.Task, error) {
	return nil, errRepository
}

func newController(t *testing.T) *web.TaskController {
	t.Helper()
	controller, err := web.NewTaskController(app.NewService(&memory.Repository{}))
	if err != nil {
		t.Fatal(err)
	}
	return controller
}

func payload(t *testing.T, title string) []byte {
	t.Helper()
	data, err := json.Marshal(web.CreateTaskRequest{Title: title})
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func assertError(t *testing.T, err error, target error) {
	t.Helper()
	if !errors.Is(err, target) {
		t.Fatalf("err = %v, quiero %v", err, target)
	}
}

func TestCreateFromJSONValido(t *testing.T) {
	view, err := newController(t).CreateFromJSON(
		context.Background(),
		payload(t, "estudiar"),
	)
	if err != nil {
		t.Fatal(err)
	}
	if view.ID != 1 {
		t.Fatalf("id = %d, quiero 1", view.ID)
	}
	if view.Title != "estudiar" {
		t.Fatalf("title = %q", view.Title)
	}
	if view.Done {
		t.Fatal("done = true, quiero false")
	}
}

func TestCreateFromJSONRechazaJSONInvalido(t *testing.T) {
	_, err := newController(t).CreateFromJSON(context.Background(), []byte(`{"title":`))

	assertError(t, err, web.ErrInvalidJSON)
}

func TestCreateFromJSONRechazaCampoDesconocido(t *testing.T) {
	payload := []byte(`{"title":"estudiar","extra":1}`)

	_, err := newController(t).CreateFromJSON(context.Background(), payload)

	assertError(t, err, web.ErrInvalidJSON)
}

func TestCreateFromJSONRechazaDatosExtra(t *testing.T) {
	payload := []byte(`{"title":"estudiar"} {}`)

	_, err := newController(t).CreateFromJSON(context.Background(), payload)

	assertError(t, err, web.ErrInvalidJSON)
}

func TestCreateFromJSONRechazaTituloNulo(t *testing.T) {
	_, err := newController(t).CreateFromJSON(context.Background(), []byte(`{"title":null}`))

	assertError(t, err, web.ErrInvalidInput)
}

func TestCreateFromJSONRechazaTituloEnBlanco(t *testing.T) {
	_, err := newController(t).CreateFromJSON(context.Background(), payload(t, "   "))

	assertError(t, err, web.ErrInvalidInput)
}

func TestCreateFromJSONRechazaEspacioNoSeparable(t *testing.T) {
	_, err := newController(t).CreateFromJSON(context.Background(), payload(t, "\u00a0"))

	assertError(t, err, web.ErrInvalidInput)
}

func TestCreateFromJSONAceptaDoscientosCaracteres(t *testing.T) {
	title := strings.Repeat("😀", 200)

	view, err := newController(t).CreateFromJSON(context.Background(), payload(t, title))
	if err != nil {
		t.Fatal(err)
	}
	if view.Title != title {
		t.Fatal("el titulo no se conservo")
	}
}

func TestCreateFromJSONRechazaTituloLargo(t *testing.T) {
	title := strings.Repeat("😀", 201)

	_, err := newController(t).CreateFromJSON(context.Background(), payload(t, title))

	assertError(t, err, web.ErrInvalidInput)
}

func TestCreateFromJSONConservaEspacios(t *testing.T) {
	view, err := newController(t).CreateFromJSON(
		context.Background(),
		payload(t, "  estudiar  "),
	)
	if err != nil {
		t.Fatal(err)
	}
	if view.Title != "  estudiar  " {
		t.Fatalf("title = %q", view.Title)
	}
}

func TestListDevuelveDTOs(t *testing.T) {
	controller := newController(t)
	if _, err := controller.CreateFromJSON(context.Background(), payload(t, "uno")); err != nil {
		t.Fatal(err)
	}

	views, err := controller.List(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if len(views) != 1 || views[0].Title != "uno" {
		t.Fatalf("views = %+v", views)
	}
}

func TestCreatePropagaElErrorDelRepositorio(t *testing.T) {
	controller, err := web.NewTaskController(app.NewService(failingRepository{}))
	if err != nil {
		t.Fatal(err)
	}

	_, err = controller.CreateFromJSON(context.Background(), payload(t, "estudiar"))

	if !errors.Is(err, errRepository) {
		t.Fatalf("err = %v, quiero el error del repositorio", err)
	}
}
