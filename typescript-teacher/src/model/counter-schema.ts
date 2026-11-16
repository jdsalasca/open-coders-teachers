import { z } from "zod";

/** Esquema del estado que llega desde fuera. */
export const counterSchema = z.object({
  value: z.number().int().nonnegative(),
});

/** Estado validado. */
export type CounterPayload = z.infer<typeof counterSchema>;

/**
 * Valida un payload externo y devuelve el estado tipado.
 *
 * @param input - dato sin tipo de confianza
 * @returns estado validado
 */
export function parseCounter(input: unknown): CounterPayload {
  return counterSchema.parse(input);
}
