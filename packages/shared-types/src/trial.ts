import { z } from "zod";
import { CouplingMatrixSchema } from "./coupling.js";
import { HingeAngle, StripSchema } from "./strip.js";

export const TrialResponseSchema = z.object({
  trialId: z.string().uuid(),
  subjectId: z.string().min(1).max(64),
  strip: StripSchema,
  presentedHinge: z.number().int().nonnegative(),
  presentedAngle: HingeAngle,
  predictedAngles: z.array(HingeAngle),
  predictedCoupledHinges: z.array(z.number().int().nonnegative()),
  confidence: z.number().min(0).max(100),
  rtMs: z.number().nonnegative(),
  timestamp: z.string().datetime(),
  device: z.object({
    userAgent: z.string(),
    viewportWidth: z.number().int().positive(),
    viewportHeight: z.number().int().positive(),
  }),
  experimentVersion: z.string(),
});

export const SessionDataSchema = z.object({
  sessionId: z.string().uuid(),
  subjectId: z.string().min(1).max(64),
  startedAt: z.string().datetime(),
  completedAt: z.string().datetime().optional(),
  trials: z.array(TrialResponseSchema),
  estimatedCoupling: CouplingMatrixSchema.optional(),
  notes: z.string().optional(),
});

export type TrialResponse = z.infer<typeof TrialResponseSchema>;
export type SessionData = z.infer<typeof SessionDataSchema>;
