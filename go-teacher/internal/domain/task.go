// Package domain define las entidades, la paginacion y los puertos del negocio.
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

// ErrInvalidPage indica una paginacion fuera de rango.
var ErrInvalidPage = errors.New("limit debe estar entre 1 y 100 y offset no puede ser negativo")

const (
	// MaxTitleLength es el maximo de caracteres (runas) del titulo.
	MaxTitleLength = 200
	// DefaultPageSize es el limite que usa la API cuando no se indica.
	DefaultPageSize = 20
	// MaxPageSize es el limite maximo que acepta la API.
	MaxPageSize = 100
)

// ValidateTitle valida las invariantes del titulo.
func ValidateTitle(title string) error {
	if !utf8.ValidString(title) {
		return ErrInvalidUTF8
	}
	if strings.TrimSpace(title) == "" {
		return ErrEmptyTitle
	}
	if utf8.RuneCountInString(title) > MaxTitleLength {
		return ErrTitleTooLong
	}
	return nil
}

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
	if err := ValidateTitle(title); err != nil {
		return Task{}, err
	}
	return Task{id: id, title: title, done: done}, nil
}

// ID devuelve el identificador unico.
func (t Task) ID() int { return t.id }

// Title devuelve el titulo original, sin recortar.
func (t Task) Title() string { return t.title }

// Done indica si la tarea esta completada.
func (t Task) Done() bool { return t.done }

// Page es una pagina de resultados.
type Page struct {
	// Limit es el maximo de tareas a devolver (1..MaxPageSize).
	Limit int
	// Offset es cuantas tareas saltar (>= 0).
	Offset int
}

// NewPage valida la paginacion.
func NewPage(limit, offset int) (Page, error) {
	if limit < 1 || limit > MaxPageSize || offset < 0 {
		return Page{}, ErrInvalidPage
	}
	return Page{Limit: limit, Offset: offset}, nil
}

// CreateResult es el resultado de crear o recuperar una tarea.
type CreateResult struct {
	// Task es la tarea creada o la existente para la clave.
	Task Task
	// Created indica si la tarea se creo en esta llamada.
	Created bool
}

// RepositoryPort es el puerto de persistencia: asigna ids, pagina y lista tareas.
type RepositoryPort interface {
	// Create crea una tarea; una clave de idempotencia repetida devuelve la original.
	Create(ctx context.Context, title, key string) (CreateResult, error)
	// List devuelve una pagina de tareas ordenada por id.
	List(ctx context.Context, page Page) ([]Task, error)
}
