// Package domain define las entidades y los puertos del negocio.
package domain

// Task es una unidad de trabajo.
type Task struct {
	ID    int
	Title string
	Done  bool
}

// RepositoryPort es el puerto de persistencia: lo implementa la infraestructura.
type RepositoryPort interface {
	Save(task Task)
	All() []Task
}
