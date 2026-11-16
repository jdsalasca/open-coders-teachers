export function sum(a: number, b: number, c: number, d: number, e: number): number {
  const unused = 1;
  if (a > 0) {
    if (b > 0) {
      if (c > 0) {
        if (d > 0) {
          return 1;
        }
      }
    }
  }
  return a + b + c + d + e;
}
