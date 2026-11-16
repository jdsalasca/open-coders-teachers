// Package app contiene los casos de uso: depende solo del dominio.
package app

import (
	"context"

	"teachers/goteacher/internal/domain"
)

// Service orquesta tareas sobre el puerto del dominio.
type Service struct {
	repo domain.RepositoryPort
}

// NewService inyecta el puerto de persistencia.
func NewService(repo domain.RepositoryPort) *Service {
	return &Service{repo: repo}
}

// Add crea una tarea con id asignado por el repositorio.
func (s *Service) Add(ctx context.Context, title string) (domain.Task, error) {
	return s.repo.Add(ctx, title)
}

// List devuelve las tareas guardadas.
func (s *Service) List(ctx context.Context) ([]domain.Task, error) {
	return s.repo.All(ctx)
}
