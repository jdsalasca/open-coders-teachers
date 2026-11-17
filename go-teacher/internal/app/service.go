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

// Add crea una tarea; una clave de idempotencia repetida devuelve la original.
func (s *Service) Add(ctx context.Context, title, key string) (domain.CreateResult, error) {
	return s.repo.Create(ctx, title, key)
}

// List devuelve una pagina de tareas ordenada por id.
func (s *Service) List(ctx context.Context, page domain.Page) ([]domain.Task, error) {
	if _, err := domain.NewPage(page.Limit, page.Offset); err != nil {
		return nil, err
	}
	return s.repo.List(ctx, page)
}
