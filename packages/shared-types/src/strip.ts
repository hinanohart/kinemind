import { z } from "zod";

export const HingeAngle = z
  .number()
  .min(-Math.PI)
  .max(Math.PI)
  .describe("Hinge dihedral angle in radians; positive = mountain, negative = valley");

export const CellLength = z
  .number()
  .positive()
  .finite()
  .describe("Length of a cell measured along the chain direction in normalized units");

export const StripSchema = z
  .object({
    id: z.string().uuid(),
    nCells: z.number().int().min(2).max(50),
    cellLengths: z.array(CellLength).min(2).max(50),
    angleMax: HingeAngle.refine((x) => x > 0, {
      message: "angleMax must be positive",
    }),
    thickness: z.number().positive().default(0.001),
  })
  .refine((data) => data.cellLengths.length === data.nCells, {
    message: "cellLengths length must equal nCells",
  });

export const StripStateSchema = z.object({
  stripId: z.string().uuid(),
  thetas: z.array(HingeAngle),
});

export type Strip = z.infer<typeof StripSchema>;
export type StripState = z.infer<typeof StripStateSchema>;
