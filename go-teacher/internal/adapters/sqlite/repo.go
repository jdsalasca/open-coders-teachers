// Package sqlite implementa el puerto de tareas sobre SQLite.
package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "modernc.org/sqlite"

	"teachers/goteacher/internal/domain"
)

// ErrIDOutOfRange senala un id que no entra en int.
var ErrIDOutOfRange = errors.New("id fuera de rango")

// Repository guarda tareas en SQLite.
type Repository struct {
	db *sql.DB
}

// sqliteDSN fuerza transacciones IMMEDIATE para serializar escritores.
func sqliteDSN(path string) string {
	if path == ":memory:" || strings.HasPrefix(path, "file::memory:") {
		return path
	}
	separator := "?"
	if strings.Contains(path, "?") {
		separator = "&"
	}
	return path + separator + "_txlock=immediate"
}

// Open abre la base, configura WAL y crea el esquema.
func Open(path string) (*Repository, error) {
	db, err := sql.Open("sqlite", sqliteDSN(path))
	if err != nil {
		return nil, fmt.Errorf("abrir sqlite: %w", err)
	}
	db.SetMaxOpenConns(1)
	repo := &Repository{db: db}
	if err := repo.init(context.Background()); err != nil {
		_ = db.Close()
		return nil, err
	}
	return repo, nil
}

func (r *Repository) init(ctx context.Context) error {
	statements := []string{
		`PRAGMA journal_mode = WAL`,
		`PRAGMA busy_timeout = 5000`,
		`PRAGMA foreign_keys = ON`,
		`CREATE TABLE IF NOT EXISTS tasks (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			done INTEGER NOT NULL DEFAULT 0
		)`,
		`CREATE TABLE IF NOT EXISTS idempotency (
			key TEXT PRIMARY KEY,
			task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE
		)`,
	}
	for _, statement := range statements {
		if _, err := r.db.ExecContext(ctx, statement); err != nil {
			return fmt.Errorf("inicializar sqlite: %w", err)
		}
	}
	return nil
}

// Close cierra la base.
func (r *Repository) Close() error {
	if err := r.db.Close(); err != nil {
		return fmt.Errorf("cerrar sqlite: %w", err)
	}
	return nil
}

// Create inserta una tarea; una clave repetida devuelve la original.
func (r *Repository) Create(
	ctx context.Context,
	title string,
	key string,
) (domain.CreateResult, error) {
	if err := ctx.Err(); err != nil {
		return domain.CreateResult{}, err
	}
	if err := domain.ValidateTitle(title); err != nil {
		return domain.CreateResult{}, err
	}
	if key == "" {
		return r.insert(ctx, title)
	}
	return r.createWithKey(ctx, title, key)
}

func (r *Repository) insert(ctx context.Context, title string) (domain.CreateResult, error) {
	result, err := r.db.ExecContext(ctx, `INSERT INTO tasks (title, done) VALUES (?, 0)`, title)
	if err != nil {
		return domain.CreateResult{}, fmt.Errorf("insertar tarea: %w", err)
	}
	id, err := result.LastInsertId()
	if err != nil {
		return domain.CreateResult{}, fmt.Errorf("leer id: %w", err)
	}
	task, err := newTask(id, title, false)
	if err != nil {
		return domain.CreateResult{}, err
	}
	return domain.CreateResult{Task: task, Created: true}, nil
}

func (r *Repository) createWithKey(
	ctx context.Context,
	title string,
	key string,
) (domain.CreateResult, error) {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return domain.CreateResult{}, fmt.Errorf("iniciar operacion: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	task, found, err := findKey(ctx, tx, key)
	if err != nil {
		return domain.CreateResult{}, err
	}
	if found {
		if err := tx.Commit(); err != nil {
			return domain.CreateResult{}, fmt.Errorf("confirmar: %w", err)
		}
		return domain.CreateResult{Task: task, Created: false}, nil
	}

	task, err = insertTask(ctx, tx, title, key)
	if err != nil {
		return domain.CreateResult{}, err
	}
	if err := tx.Commit(); err != nil {
		return domain.CreateResult{}, fmt.Errorf("confirmar: %w", err)
	}
	return domain.CreateResult{Task: task, Created: true}, nil
}

func findKey(ctx context.Context, tx *sql.Tx, key string) (domain.Task, bool, error) {
	var id int64
	err := tx.QueryRowContext(ctx, `SELECT task_id FROM idempotency WHERE key = ?`, key).Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		return domain.Task{}, false, nil
	}
	if err != nil {
		return domain.Task{}, false, fmt.Errorf("buscar clave: %w", err)
	}
	task, err := taskByID(ctx, tx, id)
	if err != nil {
		return domain.Task{}, false, err
	}
	return task, true, nil
}

func insertTask(
	ctx context.Context,
	tx *sql.Tx,
	title string,
	key string,
) (domain.Task, error) {
	result, err := tx.ExecContext(ctx, `INSERT INTO tasks (title, done) VALUES (?, 0)`, title)
	if err != nil {
		return domain.Task{}, fmt.Errorf("insertar tarea: %w", err)
	}
	id, err := result.LastInsertId()
	if err != nil {
		return domain.Task{}, fmt.Errorf("leer id: %w", err)
	}
	if _, err := tx.ExecContext(
		ctx,
		`INSERT INTO idempotency (key, task_id) VALUES (?, ?)`,
		key,
		id,
	); err != nil {
		return domain.Task{}, fmt.Errorf("guardar clave: %w", err)
	}
	return newTask(id, title, false)
}

func newTask(id int64, title string, done bool) (domain.Task, error) {
	value, err := toInt(id)
	if err != nil {
		return domain.Task{}, err
	}
	return domain.NewTask(value, title, done)
}

func toInt(value int64) (int, error) {
	if value < 1 || value > int64(int(^uint(0)>>1)) {
		return 0, fmt.Errorf("%w: %d", ErrIDOutOfRange, value)
	}
	return int(value), nil
}

func taskByID(ctx context.Context, tx *sql.Tx, id int64) (domain.Task, error) {
	var title string
	var done int
	if err := tx.QueryRowContext(
		ctx,
		`SELECT title, done FROM tasks WHERE id = ?`,
		id,
	).Scan(&title, &done); err != nil {
		return domain.Task{}, fmt.Errorf("leer tarea: %w", err)
	}
	return newTask(id, title, done != 0)
}

// List devuelve una pagina ordenada por id.
func (r *Repository) List(ctx context.Context, page domain.Page) ([]domain.Task, error) {
	if _, err := domain.NewPage(page.Limit, page.Offset); err != nil {
		return nil, err
	}
	rows, err := r.db.QueryContext(
		ctx,
		`SELECT id, title, done FROM tasks ORDER BY id LIMIT ? OFFSET ?`,
		page.Limit,
		page.Offset,
	)
	if err != nil {
		return nil, fmt.Errorf("listar tareas: %w", err)
	}
	defer func() { _ = rows.Close() }()

	tasks := make([]domain.Task, 0, page.Limit)
	for rows.Next() {
		var id int64
		var title string
		var done int
		if err := rows.Scan(&id, &title, &done); err != nil {
			return nil, fmt.Errorf("leer tarea: %w", err)
		}
		task, err := newTask(id, title, done != 0)
		if err != nil {
			return nil, err
		}
		tasks = append(tasks, task)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("recorrer tareas: %w", err)
	}
	return tasks, nil
}
