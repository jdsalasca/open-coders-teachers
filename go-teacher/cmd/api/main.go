// Command api es el composition root: unica pieza que conoce todas las capas.
package main

import (
	"fmt"
	"log"

	"teachers/goteacher/internal/adapters/memory"
	"teachers/goteacher/internal/app"
)

func main() {
	service := app.NewService(&memory.Repository{})
	if _, err := service.Add("estudiar"); err != nil {
		log.Fatal(err)
	}
	tasks, err := service.List()
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println(tasks)
}
