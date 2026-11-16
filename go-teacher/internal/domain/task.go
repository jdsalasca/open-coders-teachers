// Package domain define las entidades y los puertos del negocio.
package domain

import (
	"context"
	"errors"
	"strings"
)

// ErrInvalidID indica un id no positivo.
var ErrInvalidID = errors.New("el id debe ser positivo")

// ErrEmptyTitle indica un titulo vacio.
var ErrEmptyTitle = errors.New("el titulo no puede estar vacio")

// Task es una unidad de trabajo.
type Task struct {
	ID    int
	Title string
	Done  bool
}

// NewTask valida y construye una tarea.
func NewTask(id int, title string) (Task, error) {
	if id < 1 {
		return Task{}, ErrInvalidID
	}
	if strings.TrimSpace(title) == "" {
		return Task{}, ErrEmptyTitle
	}
	return Task{ID: id, Title: title}, nil
}

// RepositoryPort es el puerto de persistencia: asigna ids y lista tareas.
type RepositoryPort interface {
	Add(ctx context.Context, title string) (Task, error)
	All(ctx context.Context) ([]Task, error)
}
