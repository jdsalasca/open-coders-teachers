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
	keys  map[string]domain.Task
}

// Create asigna un id unico; una clave repetida devuelve la tarea original.
func (r *Repository) Create(
	ctx context.Context,
	title string,
	key string,
) (domain.CreateResult, error) {
	if err := ctx.Err(); err != nil {
		return domain.CreateResult{}, err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if err := ctx.Err(); err != nil {
		return domain.CreateResult{}, err
	}

	if task, ok := r.keys[key]; ok && key != "" {
		return domain.CreateResult{Task: task, Created: false}, nil
	}
	task, err := domain.NewTask(len(r.tasks)+1, title, false)
	if err != nil {
		return domain.CreateResult{}, err
	}
	r.tasks = append(r.tasks, task)
	if key != "" {
		if r.keys == nil {
			r.keys = make(map[string]domain.Task)
		}
		r.keys[key] = task
	}
	return domain.CreateResult{Task: task, Created: true}, nil
}

// List devuelve una pagina ordenada por id.
func (r *Repository) List(ctx context.Context, page domain.Page) ([]domain.Task, error) {
	if _, err := domain.NewPage(page.Limit, page.Offset); err != nil {
		return nil, err
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	start := min(page.Offset, len(r.tasks))
	end := min(start+page.Limit, len(r.tasks))
	out := make([]domain.Task, end-start)
	copy(out, r.tasks[start:end])
	return out, nil
}
