// Package app contiene los casos de uso: depende solo del dominio.
package app

import "teachers/goteacher/internal/domain"

// Service orquesta tareas sobre el puerto del dominio.
type Service struct {
	repo domain.Repository
}

// NewService inyecta el puerto de persistencia.
func NewService(repo domain.Repository) *Service {
	return &Service{repo: repo}
}

// Add crea una tarea y la guarda.
func (s *Service) Add(title string) domain.Task {
	task := domain.Task{ID: len(s.repo.All()) + 1, Title: title}
	s.repo.Save(task)
	return task
}

// List devuelve las tareas guardadas.
func (s *Service) List() []domain.Task {
	return s.repo.All()
}
