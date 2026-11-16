// Command api es el composition root: unica pieza que conoce todas las capas.
package main

import (
	"fmt"

	"teachers/goteacher/internal/adapters/memory"
	"teachers/goteacher/internal/app"
)

func main() {
	service := app.NewService(&memory.Repository{})
	service.Add("estudiar")
	fmt.Println(service.List())
}
