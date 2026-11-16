package domain_test

import (
	"errors"
	"testing"

	"teachers/goteacher/internal/domain"
)

func TestNewTaskValida(t *testing.T) {
	task, err := domain.NewTask(1, "estudiar")
	if err != nil {
		t.Fatal(err)
	}
	if task.Title != "estudiar" {
		t.Fatalf("title = %q", task.Title)
	}
}

func TestNewTaskRechazaIDInvalido(t *testing.T) {
	_, err := domain.NewTask(0, "estudiar")
	if !errors.Is(err, domain.ErrInvalidID) {
		t.Fatalf("err = %v, quiero ErrInvalidID", err)
	}
}

func TestNewTaskRechazaTituloVacio(t *testing.T) {
	_, err := domain.NewTask(1, "   ")
	if !errors.Is(err, domain.ErrEmptyTitle) {
		t.Fatalf("err = %v, quiero ErrEmptyTitle", err)
	}
}
