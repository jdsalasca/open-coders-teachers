// Package domain define las entidades y los puertos del negocio.
package domain

import (
	"context"
	"errors"
	"strings"
	"unicode/utf8"
)

// ErrInvalidID indica un id no positivo.
var ErrInvalidID = errors.New("el id debe ser positivo")

// ErrEmptyTitle indica un titulo vacio.
var ErrEmptyTitle = errors.New("el titulo no puede estar vacio")

// ErrInvalidUTF8 indica un titulo que no es UTF-8 valido.
var ErrInvalidUTF8 = errors.New("el titulo debe ser UTF-8 valido")

// ErrTitleTooLong indica un titulo que supera MaxTitleLength.
var ErrTitleTooLong = errors.New("el titulo supera los 200 caracteres")

// MaxTitleLength es el maximo de caracteres (runas) del titulo.
const MaxTitleLength = 200

// Task es una unidad de trabajo. El valor cero no es valido: usa NewTask.
type Task struct {
	id    int
	title string
	done  bool
}

// NewTask valida y construye una tarea.
func NewTask(id int, title string, done bool) (Task, error) {
	if id < 1 {
		return Task{}, ErrInvalidID
	}
	if !utf8.ValidString(title) {
		return Task{}, ErrInvalidUTF8
	}
	if strings.TrimSpace(title) == "" {
		return Task{}, ErrEmptyTitle
	}
	if utf8.RuneCountInString(title) > MaxTitleLength {
		return Task{}, ErrTitleTooLong
	}
	return Task{id: id, title: title, done: done}, nil
}

// ID devuelve el identificador unico.
func (t Task) ID() int { return t.id }

// Title devuelve el titulo original, sin recortar.
func (t Task) Title() string { return t.title }

// Done indica si la tarea esta completada.
func (t Task) Done() bool { return t.done }

// RepositoryPort es el puerto de persistencia: asigna ids y lista tareas.
type RepositoryPort interface {
	Add(ctx context.Context, title string) (Task, error)
	All(ctx context.Context) ([]Task, error)
}
