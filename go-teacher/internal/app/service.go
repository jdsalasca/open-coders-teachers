// Package app contiene los casos de uso: depende solo del dominio.
package app

import (
	"errors"
	"strings"

	"teachers/goteacher/internal/domain"
)

// ErrEmptyTitle indica que el titulo de la tarea esta vacio.
var ErrEmptyTitle = errors.New("el titulo no puede estar vacio")

// Service orquesta tareas sobre el puerto del dominio.
type Service struct {
	repo domain.RepositoryPort
}

// NewService inyecta el puerto de persistencia.
func NewService(repo domain.RepositoryPort) *Service {
	return &Service{repo: repo}
}

// Add crea una tarea con id unico y la guarda.
func (s *Service) Add(title string) (domain.Task, error) {
	if strings.TrimSpace(title) == "" {
		return domain.Task{}, ErrEmptyTitle
	}
	tasks, err := s.repo.All()
	if err != nil {
		return domain.Task{}, err
	}
	next := 1
	for _, task := range tasks {
		if task.ID >= next {
			next = task.ID + 1
		}
	}
	created := domain.Task{ID: next, Title: title}
	if err := s.repo.Save(created); err != nil {
		return domain.Task{}, err
	}
	return created, nil
}

// List devuelve las tareas guardadas.
func (s *Service) List() ([]domain.Task, error) {
	return s.repo.All()
}
