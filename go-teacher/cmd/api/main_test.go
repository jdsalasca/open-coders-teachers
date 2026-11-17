package main

import (
	"context"
	"net"
	"net/http"
	"testing"
)

func TestServeEsperaElApagadoAntesDeDevolver(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	entered := make(chan struct{})
	release := make(chan struct{})
	handler := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		close(entered)
		<-release
		w.WriteHeader(http.StatusNoContent)
	})
	server := newServer("", handler)
	shutdownDone := make(chan struct{})
	serveDone := make(chan error, 1)
	go func() { serveDone <- serve(server, listener, shutdownDone) }()

	requestDone := make(chan error, 1)
	go func() {
		response, err := http.Get("http://" + listener.Addr().String())
		if err == nil {
			_ = response.Body.Close()
		}
		requestDone <- err
	}()
	<-entered

	shutdownDoneByServer := make(chan error, 1)
	go func() { shutdownDoneByServer <- server.Shutdown(context.Background()) }()
	select {
	case err := <-serveDone:
		t.Fatalf("serve devolvio antes de terminar el handler: %v", err)
	default:
	}

	close(release)
	if err := <-shutdownDoneByServer; err != nil {
		t.Fatal(err)
	}
	close(shutdownDone)

	if err := <-serveDone; err != nil {
		t.Fatal(err)
	}
	if err := <-requestDone; err != nil {
		t.Fatal(err)
	}
}
