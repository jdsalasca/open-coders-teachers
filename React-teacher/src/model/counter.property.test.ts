import fc from "fast-check";
import { describe, expect, it } from "vitest";

import { inc } from "./counter";

describe("counter (propiedades)", () => {
  it("incrementar siempre suma uno y no muta el estado", () => {
    fc.assert(
      fc.property(fc.integer({ min: -1_000_000, max: 1_000_000 }), (value) => {
        const state = { value };

        expect(inc(state).value).toBe(value + 1);
        expect(state.value).toBe(value);
      }),
    );
  });
});
