package domain_test

import (
	"errors"
	"strings"
	"testing"

	"teachers/goteacher/internal/domain"
)

func TestNewTaskValida(t *testing.T) {
	task, err := domain.NewTask(1, "estudiar", false)
	if err != nil {
		t.Fatal(err)
	}
	if task.ID() != 1 {
		t.Fatalf("id = %d, quiero 1", task.ID())
	}
	if task.Title() != "estudiar" {
		t.Fatalf("title = %q", task.Title())
	}
	if task.Done() {
		t.Fatal("done = true, quiero false")
	}
}

func TestNewTaskConservaEspacios(t *testing.T) {
	task, err := domain.NewTask(1, "  estudiar  ", false)
	if err != nil {
		t.Fatal(err)
	}
	if task.Title() != "  estudiar  " {
		t.Fatalf("title = %q", task.Title())
	}
}

func TestNewTaskAceptaElMaximoDeCaracteres(t *testing.T) {
	title := strings.Repeat("😀", domain.MaxTitleLength)

	if _, err := domain.NewTask(1, title, false); err != nil {
		t.Fatalf("err = %v, quiero nil", err)
	}
}

func TestNewTaskRechazaIDInvalido(t *testing.T) {
	_, err := domain.NewTask(0, "estudiar", false)
	if !errors.Is(err, domain.ErrInvalidID) {
		t.Fatalf("err = %v, quiero ErrInvalidID", err)
	}
}

func TestNewTaskRechazaTituloVacio(t *testing.T) {
	_, err := domain.NewTask(1, "   ", false)
	if !errors.Is(err, domain.ErrEmptyTitle) {
		t.Fatalf("err = %v, quiero ErrEmptyTitle", err)
	}
}

func TestNewTaskRechazaTituloLargo(t *testing.T) {
	title := strings.Repeat("😀", domain.MaxTitleLength+1)

	_, err := domain.NewTask(1, title, false)

	if !errors.Is(err, domain.ErrTitleTooLong) {
		t.Fatalf("err = %v, quiero ErrTitleTooLong", err)
	}
}

func TestNewTaskRechazaUTF8Invalido(t *testing.T) {
	_, err := domain.NewTask(1, string([]byte{0xff}), false)

	if !errors.Is(err, domain.ErrInvalidUTF8) {
		t.Fatalf("err = %v, quiero ErrInvalidUTF8", err)
	}
}

func TestNewTaskRechazaEspacioNoSeparable(t *testing.T) {
	_, err := domain.NewTask(1, "\u00a0", false)

	if !errors.Is(err, domain.ErrEmptyTitle) {
		t.Fatalf("err = %v, quiero ErrEmptyTitle", err)
	}
}

func FuzzNewTask(f *testing.F) {
	f.Add(1, "estudiar")
	f.Fuzz(func(t *testing.T, id int, title string) {
		task, err := domain.NewTask(id, title, false)
		if err != nil {
			return
		}
		if task.ID() != id {
			t.Fatalf("id = %d, quiero %d", task.ID(), id)
		}
		if task.Title() != title {
			t.Fatal("el titulo no se conservo")
		}
	})
}
