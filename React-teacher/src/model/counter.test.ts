import { describe, expect, it } from "vitest";

import { inc, initialCounter } from "./counter";

describe("counter", () => {
  it("arranca en cero", () => {
    expect(initialCounter()).toEqual({ value: 0 });
  });

  it("incrementa sin mutar", () => {
    const state = initialCounter();

    expect(inc(state)).toEqual({ value: 1 });
    expect(state.value).toBe(0);
  });

  it("satura en el maximo entero seguro", () => {
    const state = { value: Number.MAX_SAFE_INTEGER };

    expect(inc(state)).toEqual({ value: Number.MAX_SAFE_INTEGER });
  });
});
