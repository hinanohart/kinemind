import { z } from "zod";

/**
 * Zod schema for TreeStrip: a rooted tree of origami cells.
 * Extends the path-graph strip to arbitrary tree topologies.
 */
export const TreeStripSchema = z
  .object({
    nNodes: z.number().int().min(2).max(100),
    /** parents[0] must be null (root); parents[i] is the parent index for i > 0. */
    parents: z.array(z.union([z.number().int().nonnegative(), z.null()])).min(2),
    /** Edge lengths indexed by child node (length = nNodes - 1). */
    edgeLengths: z.array(z.number().positive().finite()).min(1),
    /** Optional per-edge hinge axes (length = nNodes - 1). */
    hingeAxes: z.array(z.tuple([z.number(), z.number(), z.number()])).optional(),
    angleMax: z.number().positive().max(Math.PI),
  })
  .refine((d) => d.parents.length === d.nNodes, {
    message: "parents length must equal nNodes",
  })
  .refine((d) => d.edgeLengths.length === d.nNodes - 1, {
    message: "edgeLengths length must equal nNodes - 1",
  })
  .refine((d) => d.parents[0] === null, {
    message: "parents[0] must be null (root node)",
  })
  .refine((d) => d.hingeAxes === undefined || d.hingeAxes.length === d.nNodes - 1, {
    message: "hingeAxes length must equal nNodes - 1 when provided",
  });

export type TreeStrip = z.infer<typeof TreeStripSchema>;
