package web_test

import (
	"net/http"
	"path/filepath"
	"testing"

	"teachers/goteacher/internal/adapters/sqlite"
	"teachers/goteacher/internal/app"
	"teachers/goteacher/internal/web"
)

func newSQLiteAPI(t *testing.T) http.Handler {
	t.Helper()
	repository, err := sqlite.Open(filepath.Join(t.TempDir(), "tasks.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := repository.Close(); err != nil {
			t.Errorf("cerrar: %v", err)
		}
	})
	controller, err := web.NewTaskController(app.NewService(repository))
	if err != nil {
		t.Fatal(err)
	}
	return web.NewHandler(controller)
}

type createCall struct {
	body   string
	key    string
	status int
}

func createViaAPI(t *testing.T, api http.Handler, call createCall) web.TaskView {
	t.Helper()
	recorder := serve(t, api, post(call.body, call.key))
	if recorder.Code != call.status {
		t.Fatalf("status = %d, quiero %d", recorder.Code, call.status)
	}
	return decode[web.TaskView](t, recorder)
}

func TestAPIUsaSQLite(t *testing.T) {
	api := newSQLiteAPI(t)

	created := createViaAPI(t, api, createCall{
		body:   `{"title":"estudiar"}`,
		key:    "clave",
		status: http.StatusCreated,
	})
	replay := createViaAPI(t, api, createCall{
		body:   `{"title":"otro"}`,
		key:    "clave",
		status: http.StatusOK,
	})
	if replay.ID != created.ID {
		t.Fatal("el replay debe devolver la tarea original")
	}

	list := serve(t, api, get("/tasks?limit=10&offset=0"))
	if list.Code != http.StatusOK {
		t.Fatalf("list = %d, quiero 200", list.Code)
	}
	response := decode[web.ListResponse](t, list)
	if len(response.Items) != 1 || response.Items[0].ID != created.ID {
		t.Fatalf("items = %+v", response.Items)
	}
}
