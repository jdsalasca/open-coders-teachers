// Package memory implementa el puerto de tareas en memoria.
package memory

import (
	"context"
	"sync"

	"teachers/goteacher/internal/domain"
)

// Repository guarda tareas en un slice protegido por mutex.
type Repository struct {
	mu    sync.Mutex
	tasks []domain.Task
}

// Add asigna un id unico y guarda la tarea de forma concurrente.
func (r *Repository) Add(ctx context.Context, title string) (domain.Task, error) {
	if err := ctx.Err(); err != nil {
		return domain.Task{}, err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if err := ctx.Err(); err != nil {
		return domain.Task{}, err
	}

	task, err := domain.NewTask(len(r.tasks)+1, title, false)
	if err != nil {
		return domain.Task{}, err
	}
	r.tasks = append(r.tasks, task)
	return task, nil
}

// All devuelve una copia de las tareas.
func (r *Repository) All(ctx context.Context) ([]domain.Task, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	out := make([]domain.Task, len(r.tasks))
	copy(out, r.tasks)
	return out, nil
}
