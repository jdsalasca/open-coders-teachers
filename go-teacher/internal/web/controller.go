// Package web es el adaptador de entrada: valida DTOs y devuelve DTOs.
package web

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"

	"github.com/go-playground/validator/v10"

	"teachers/goteacher/internal/app"
	"teachers/goteacher/internal/domain"
)

// ErrInvalidJSON indica un payload que no es JSON valido.
var ErrInvalidJSON = errors.New("payload invalido")

// ErrInvalidInput indica datos que no cumplen la validacion.
var ErrInvalidInput = errors.New("datos invalidos")

// CreateTaskRequest es el payload de creacion de tarea.
type CreateTaskRequest struct {
	// Title es el titulo obligatorio, no blanco y de hasta 200 caracteres.
	Title string `json:"title" validate:"required,max=200,notblank"`
}

// TaskView es el DTO de salida de una tarea.
type TaskView struct {
	// ID es el identificador unico.
	ID int `json:"id"`
	// Title es el titulo de la tarea.
	Title string `json:"title"`
	// Done indica si la tarea esta completada.
	Done bool `json:"done"`
}

// NewTaskView convierte una entidad del dominio en DTO.
func NewTaskView(task domain.Task) TaskView {
	return TaskView{ID: task.ID(), Title: task.Title(), Done: task.Done()}
}

// TaskController valida la entrada y delega en el caso de uso.
type TaskController struct {
	service  *app.Service
	validate *validator.Validate
}

// NewTaskController inyecta el caso de uso y registra las reglas.
func NewTaskController(service *app.Service) (*TaskController, error) {
	validate := validator.New()
	if err := validate.RegisterValidation("notblank", notBlank); err != nil {
		return nil, fmt.Errorf("registrar notblank: %w", err)
	}
	return &TaskController{service: service, validate: validate}, nil
}

func notBlank(field validator.FieldLevel) bool {
	return strings.TrimSpace(field.Field().String()) != ""
}

// CreateFromJSON deserializa, valida y crea la tarea.
func (c *TaskController) CreateFromJSON(ctx context.Context, payload []byte) (TaskView, error) {
	request, err := decodeRequest(payload)
	if err != nil {
		return TaskView{}, err
	}
	return c.Create(ctx, request)
}

func decodeRequest(payload []byte) (CreateTaskRequest, error) {
	var request CreateTaskRequest
	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&request); err != nil {
		return CreateTaskRequest{}, fmt.Errorf("%w: %w", ErrInvalidJSON, err)
	}
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		return CreateTaskRequest{}, fmt.Errorf("%w: datos extra", ErrInvalidJSON)
	}
	return request, nil
}

// Create valida la peticion y devuelve el DTO creado.
func (c *TaskController) Create(ctx context.Context, request CreateTaskRequest) (TaskView, error) {
	if err := c.validate.Struct(request); err != nil {
		return TaskView{}, fmt.Errorf("%w: %w", ErrInvalidInput, err)
	}
	task, err := c.service.Add(ctx, request.Title)
	if err != nil {
		return TaskView{}, err
	}
	return NewTaskView(task), nil
}

// List devuelve las tareas como DTO.
func (c *TaskController) List(ctx context.Context) ([]TaskView, error) {
	tasks, err := c.service.List(ctx)
	if err != nil {
		return nil, err
	}
	views := make([]TaskView, len(tasks))
	for index, task := range tasks {
		views[index] = NewTaskView(task)
	}
	return views, nil
}
