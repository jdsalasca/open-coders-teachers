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
});
