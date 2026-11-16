import { describe, expect, it } from "vitest";

import { increment, initialCounter } from "./counter.js";

describe("counter", () => {
  it("arranca en cero", () => {
    expect(initialCounter()).toEqual({ value: 0 });
  });

  it("incrementa sin mutar el estado", () => {
    const state = initialCounter();
    const next = increment(state);

    expect(next.value).toBe(1);
    expect(state.value).toBe(0);
  });
});
