package web

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"mime"
	"net/http"
	"net/url"
	"strconv"

	"teachers/goteacher/internal/domain"
)

// ErrInvalidQueryParameter senala un parametro de consulta invalido.
var ErrInvalidQueryParameter = errors.New("parametro de consulta invalido")

// MaxBodyBytes es el tamano maximo del payload HTTP.
const MaxBodyBytes = 1 << 20

// ListResponse es la pagina de tareas que devuelve la API.
type ListResponse struct {
	// Items son las tareas de la pagina.
	Items []TaskView `json:"items"`
	// Limit es el limite aplicado.
	Limit int `json:"limit"`
	// Offset es el desplazamiento aplicado.
	Offset int `json:"offset"`
}

type handler struct {
	controller *TaskController
}

// NewHandler construye el router HTTP de la API.
func NewHandler(controller *TaskController) http.Handler {
	api := &handler{controller: controller}
	mux := http.NewServeMux()
	mux.HandleFunc("POST /tasks", api.create)
	mux.HandleFunc("GET /tasks", api.list)
	mux.HandleFunc("GET /healthz", api.health)
	return mux
}

func (h *handler) create(w http.ResponseWriter, r *http.Request) {
	if !isJSON(r.Header.Get("Content-Type")) {
		writeError(w, http.StatusUnsupportedMediaType, "content-type debe ser application/json")
		return
	}
	body := http.MaxBytesReader(w, r.Body, MaxBodyBytes)
	payload, err := io.ReadAll(body)
	if err != nil {
		if _, ok := errors.AsType[*http.MaxBytesError](err); ok {
			writeError(w, http.StatusRequestEntityTooLarge, "payload demasiado grande")
			return
		}
		writeError(w, http.StatusBadRequest, "no pude leer el payload")
		return
	}

	view, created, err := h.controller.CreateFromJSON(
		r.Context(),
		payload,
		r.Header.Get("Idempotency-Key"),
	)
	if err != nil {
		writeControllerError(w, err)
		return
	}
	status := http.StatusOK
	if created {
		status = http.StatusCreated
	}
	w.Header().Set("Location", fmt.Sprintf("/tasks/%d", view.ID))
	writeJSON(w, status, view)
}

func (h *handler) list(w http.ResponseWriter, r *http.Request) {
	page, err := pageFromQuery(r.URL.Query())
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	views, err := h.controller.List(r.Context(), page)
	if err != nil {
		writeControllerError(w, err)
		return
	}
	writeJSON(
		w,
		http.StatusOK,
		ListResponse{Items: views, Limit: page.Limit, Offset: page.Offset},
	)
}

func (h *handler) health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func isJSON(contentType string) bool {
	mediaType, _, err := mime.ParseMediaType(contentType)
	return err == nil && mediaType == "application/json"
}

func pageFromQuery(values url.Values) (domain.Page, error) {
	limit, err := queryInt(values, "limit", domain.DefaultPageSize)
	if err != nil {
		return domain.Page{}, err
	}
	offset, err := queryInt(values, "offset", 0)
	if err != nil {
		return domain.Page{}, err
	}
	return domain.NewPage(limit, offset)
}

func queryInt(values url.Values, name string, fallback int) (int, error) {
	raw := values.Get(name)
	if raw == "" {
		return fallback, nil
	}
	value, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("%w: %s", ErrInvalidQueryParameter, name)
	}
	return value, nil
}

func writeControllerError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrInvalidJSON) || errors.Is(err, ErrInvalidInput) {
		writeError(w, http.StatusBadRequest, "datos invalidos")
		return
	}
	log.Printf("error interno: %v", err)
	writeError(w, http.StatusInternalServerError, "error interno")
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(value); err != nil {
		log.Printf("escribir respuesta: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
