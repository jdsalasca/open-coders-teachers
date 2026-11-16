// Package main es un fixture con violaciones a proposito.
package main

import "fmt"

func many(a, b, c, d, e int) int {
	fmt.Println(a, b, c, d, e)
	return 0
}

func main() {
	fmt.Println(many(1, 2, 3, 4, 5))
}
