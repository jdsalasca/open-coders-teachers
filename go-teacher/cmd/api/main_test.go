package main

import (
	"context"
	"net"
	"net/http"
	"testing"
)

func blockingHandler(entered chan struct{}, release chan struct{}) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		close(entered)
		<-release
		w.WriteHeader(http.StatusNoContent)
	})
}

func sendRequest(listener net.Listener, done chan<- error) {
	request, err := http.NewRequestWithContext(
		context.Background(),
		http.MethodGet,
		"http://"+listener.Addr().String(),
		nil,
	)
	if err != nil {
		done <- err
		return
	}
	response, err := http.DefaultClient.Do(request)
	if err == nil {
		_ = response.Body.Close()
	}
	done <- err
}

func TestServeEsperaElApagadoAntesDeDevolver(t *testing.T) {
	listener, err := (&net.ListenConfig{}).Listen(context.Background(), "tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	entered := make(chan struct{})
	release := make(chan struct{})
	server := newServer("", blockingHandler(entered, release))
	shutdownDone := make(chan struct{})
	serveDone := make(chan error, 1)
	go func() { serveDone <- serve(server, listener, shutdownDone) }()

	requestDone := make(chan error, 1)
	go sendRequest(listener, requestDone)
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
