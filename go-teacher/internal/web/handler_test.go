package web_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"teachers/goteacher/internal/adapters/memory"
	"teachers/goteacher/internal/app"
	"teachers/goteacher/internal/web"
)

type request struct {
	method      string
	path        string
	contentType string
	body        string
	key         string
}

func post(body string, key string) request {
	return request{
		method:      http.MethodPost,
		path:        "/tasks",
		contentType: "application/json",
		body:        body,
		key:         key,
	}
}

func get(path string) request {
	return request{method: http.MethodGet, path: path}
}

func newAPI(t *testing.T) http.Handler {
	t.Helper()
	controller, err := web.NewTaskController(app.NewService(&memory.Repository{}))
	if err != nil {
		t.Fatal(err)
	}
	return web.NewHandler(controller)
}

func serve(t *testing.T, handler http.Handler, req request) *httptest.ResponseRecorder {
	t.Helper()
	httpRequest := httptest.NewRequestWithContext(
		context.Background(),
		req.method,
		req.path,
		strings.NewReader(req.body),
	)
	if req.contentType != "" {
		httpRequest.Header.Set("Content-Type", req.contentType)
	}
	if req.key != "" {
		httpRequest.Header.Set("Idempotency-Key", req.key)
	}
	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, httpRequest)
	return recorder
}

func decode[T any](t *testing.T, recorder *httptest.ResponseRecorder) T {
	t.Helper()
	var value T
	if err := json.NewDecoder(recorder.Body).Decode(&value); err != nil {
		t.Fatalf("decodificar respuesta: %v", err)
	}
	return value
}

func createTitles(t *testing.T, api http.Handler, titles []string) {
	t.Helper()
	for _, title := range titles {
		body := `{"title":"` + title + `"}`
		recorder := serve(t, api, post(body, ""))
		if recorder.Code != http.StatusCreated {
			t.Fatalf("crear %q: %d", title, recorder.Code)
		}
	}
}

func TestCreateDevuelve201(t *testing.T) {
	recorder := serve(t, newAPI(t), post(`{"title":"estudiar"}`, ""))

	if recorder.Code != http.StatusCreated {
		t.Fatalf("status = %d, quiero 201", recorder.Code)
	}
	if location := recorder.Header().Get("Location"); location != "/tasks/1" {
		t.Fatalf("Location = %q", location)
	}
	view := decode[web.TaskView](t, recorder)
	if view.ID != 1 || view.Title != "estudiar" {
		t.Fatalf("view = %+v", view)
	}
}

func TestCreateEsIdempotente(t *testing.T) {
	api := newAPI(t)

	first := serve(t, api, post(`{"title":"estudiar"}`, "clave"))
	second := serve(t, api, post(`{"title":"otro"}`, "clave"))

	if first.Code != http.StatusCreated {
		t.Fatalf("primera = %d, quiero 201", first.Code)
	}
	if second.Code != http.StatusOK {
		t.Fatalf("segunda = %d, quiero 200", second.Code)
	}
	firstView := decode[web.TaskView](t, first)
	secondView := decode[web.TaskView](t, second)
	if firstView.ID != secondView.ID || secondView.Title != "estudiar" {
		t.Fatalf("replay = %+v, quiero %+v", secondView, firstView)
	}
}

func TestCreateRechazaContentType(t *testing.T) {
	req := request{
		method:      http.MethodPost,
		path:        "/tasks",
		contentType: "text/plain",
		body:        `{"title":"estudiar"}`,
	}

	recorder := serve(t, newAPI(t), req)

	if recorder.Code != http.StatusUnsupportedMediaType {
		t.Fatalf("status = %d, quiero 415", recorder.Code)
	}
}

func TestCreateRechazaJSONInvalido(t *testing.T) {
	recorder := serve(t, newAPI(t), post("{", ""))

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, quiero 400", recorder.Code)
	}
}

func TestCreateRechazaPayloadGrande(t *testing.T) {
	body := `{"title":"` + strings.Repeat("x", web.MaxBodyBytes) + `"}`

	recorder := serve(t, newAPI(t), post(body, ""))

	if recorder.Code != http.StatusRequestEntityTooLarge {
		t.Fatalf("status = %d, quiero 413", recorder.Code)
	}
}

func TestCreateRechazaClaveLarga(t *testing.T) {
	key := strings.Repeat("k", web.MaxIdempotencyKeyLength+1)

	recorder := serve(t, newAPI(t), post(`{"title":"estudiar"}`, key))

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, quiero 400", recorder.Code)
	}
}

func TestCreateDevuelveErrorInternoSinDetalle(t *testing.T) {
	controller, err := web.NewTaskController(app.NewService(failingRepository{}))
	if err != nil {
		t.Fatal(err)
	}

	recorder := serve(t, web.NewHandler(controller), post(`{"title":"estudiar"}`, ""))

	if recorder.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, quiero 500", recorder.Code)
	}
	if strings.Contains(recorder.Body.String(), errRepository.Error()) {
		t.Fatal("la respuesta no debe filtrar el error interno")
	}
}

func TestListPaginado(t *testing.T) {
	api := newAPI(t)
	createTitles(t, api, []string{"uno", "dos", "tres"})

	recorder := serve(t, api, get("/tasks?limit=2&offset=1"))

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, quiero 200", recorder.Code)
	}
	response := decode[web.ListResponse](t, recorder)
	if response.Limit != 2 || response.Offset != 1 {
		t.Fatalf("pagina = %+v", response)
	}
	if len(response.Items) != 2 {
		t.Fatalf("items = %d, quiero 2", len(response.Items))
	}
	if response.Items[0].ID != 2 || response.Items[1].ID != 3 {
		t.Fatalf("items = %+v", response.Items)
	}
}

func TestListRechazaPaginacionInvalida(t *testing.T) {
	for _, path := range []string{"/tasks?limit=0", "/tasks?limit=101", "/tasks?limit=x"} {
		recorder := serve(t, newAPI(t), get(path))
		if recorder.Code != http.StatusBadRequest {
			t.Fatalf("%s: status = %d, quiero 400", path, recorder.Code)
		}
	}
}

func TestHealth(t *testing.T) {
	recorder := serve(t, newAPI(t), get("/healthz"))

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, quiero 200", recorder.Code)
	}
}

func TestRutaDesconocida(t *testing.T) {
	recorder := serve(t, newAPI(t), get("/nada"))

	if recorder.Code != http.StatusNotFound {
		t.Fatalf("status = %d, quiero 404", recorder.Code)
	}
}

func TestMetodoNoPermitido(t *testing.T) {
	req := request{
		method:      http.MethodPut,
		path:        "/tasks",
		contentType: "application/json",
		body:        "{}",
	}

	recorder := serve(t, newAPI(t), req)

	if recorder.Code != http.StatusMethodNotAllowed {
		t.Fatalf("status = %d, quiero 405", recorder.Code)
	}
}
