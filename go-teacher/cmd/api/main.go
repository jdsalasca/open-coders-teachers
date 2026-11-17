// Package main es el composition root: unica pieza que conoce todas las capas.
package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"time"

	"teachers/goteacher/internal/adapters/sqlite"
	"teachers/goteacher/internal/app"
	"teachers/goteacher/internal/web"
)

func main() {
	if err := run(); err != nil {
		log.Fatal(err)
	}
}

func run() error {
	dbPath := env("TASKS_DB", "tasks.db")
	addr := env("TASKS_ADDR", ":8080")

	repository, err := sqlite.Open(dbPath)
	if err != nil {
		return err
	}
	defer func() {
		if err := repository.Close(); err != nil {
			log.Printf("cerrar base: %v", err)
		}
	}()

	controller, err := web.NewTaskController(app.NewService(repository))
	if err != nil {
		return err
	}

	server := newServer(addr, web.NewHandler(controller))
	shutdownOnSignal(server)

	log.Printf("escuchando en %s (db %s)", addr, dbPath)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}

func newServer(addr string, handler http.Handler) *http.Server {
	return &http.Server{
		Addr:              addr,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
}

func shutdownOnSignal(server *http.Server) {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	go func() {
		defer stop()
		<-ctx.Done()
		shutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdown); err != nil {
			log.Printf("apagar servidor: %v", err)
		}
	}()
}

func env(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}
