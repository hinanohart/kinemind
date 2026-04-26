import { z } from "zod";

export const CouplingSourceSchema = z.enum([
  "analytic-mirror",
  "analytic-identity",
  "empirical-mental",
  "empirical-physical",
]);

export const CouplingMatrixSchema = z.object({
  source: CouplingSourceSchema,
  matrix: z.array(z.array(z.number())),
  nHinges: z.number().int().min(1),
  beta: z.number().min(0).max(1).optional(),
  confidence: z.array(z.array(z.number())).optional(),
});

export type CouplingMatrix = z.infer<typeof CouplingMatrixSchema>;
export type CouplingSource = z.infer<typeof CouplingSourceSchema>;
