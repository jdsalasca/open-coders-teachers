// Package main es el composition root: unica pieza que conoce todas las capas.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"teachers/goteacher/internal/adapters/memory"
	"teachers/goteacher/internal/app"
	"teachers/goteacher/internal/web"
)

func main() {
	ctx := context.Background()
	service := app.NewService(&memory.Repository{})
	controller, err := web.NewTaskController(service)
	if err != nil {
		log.Fatal(err)
	}
	if _, err := controller.CreateFromJSON(ctx, []byte(`{"title":"estudiar"}`)); err != nil {
		log.Fatal(err)
	}
	views, err := controller.List(ctx)
	if err != nil {
		log.Fatal(err)
	}
	output, err := json.Marshal(views)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println(string(output))
}
