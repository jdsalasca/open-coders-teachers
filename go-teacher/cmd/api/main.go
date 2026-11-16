// Command api es el composition root: unica pieza que conoce todas las capas.
package main

import (
	"context"
	"fmt"
	"log"

	"teachers/goteacher/internal/adapters/memory"
	"teachers/goteacher/internal/app"
)

func main() {
	ctx := context.Background()
	service := app.NewService(&memory.Repository{})
	if _, err := service.Add(ctx, "estudiar"); err != nil {
		log.Fatal(err)
	}
	tasks, err := service.List(ctx)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println(tasks)
}
