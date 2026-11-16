// Package memory implementa el puerto de tareas en memoria.
package memory

import "teachers/goteacher/internal/domain"

// Repository guarda tareas en un slice.
type Repository struct {
	tasks []domain.Task
}

// Save reemplaza por ID o agrega al final.
func (r *Repository) Save(task domain.Task) error {
	for index, item := range r.tasks {
		if item.ID == task.ID {
			r.tasks[index] = task
			return nil
		}
	}
	r.tasks = append(r.tasks, task)
	return nil
}

// All devuelve una copia de las tareas.
func (r *Repository) All() ([]domain.Task, error) {
	out := make([]domain.Task, len(r.tasks))
	copy(out, r.tasks)
	return out, nil
}
