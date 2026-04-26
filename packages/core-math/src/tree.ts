/**
 * Tree-graph generalization of 1D origami strip kinematics.
 *
 * A ``TreeStrip`` represents a rooted tree where each non-root node has
 * a parent connected by a revolute hinge joint.  A path graph P_N is a
 * special case with ``parents = [null, 0, 1, ..., N-2]``.
 *
 * Forward kinematics is computed by DFS from the root (node 0), accumulating
 * SE(3) transforms along each parent→child edge.
 *
 * Backward compatibility:
 *   ``pathGraphTree(n, L).forwardKinematics(thetas)`` produces bit-exact
 *   positions matching ``forwardKinematics(makeUniformStrip(n, L), state)``.
 *
 * Parity: matches python/origami_lab/src/origami_lab/tree.py at atol=1e-15.
 */

import { type SE3, SE3_IDENTITY, type Vec3, rot, se3Apply, se3Compose, trans } from "./se3.js";
import { CELL_Y_AXIS } from "./strip.js";

// ---- Public types ----

/**
 * Rooted tree of origami cells connected by revolute hinges.
 *
 * ``parents[i] = null`` for the root (must be node 0).
 * ``parents[i] = p`` for child node i with parent p.
 * ``edgeLengths[i]`` is the length of the edge from parent[i] to node i;
 * indexed by child, so length = nNodes - 1.
 */
export interface TreeStrip {
  readonly nNodes: number;
  /** Length nNodes; parents[0] must be null (root). */
  readonly parents: readonly (number | null)[];
  /** Length nNodes - 1; edge length indexed by child node. */
  readonly edgeLengths: readonly number[];
  /** Optional per-edge hinge axis (defaults to [0, 1, 0] when omitted). */
  readonly hingeAxes?: readonly Vec3[];
  /** Hard limit on |theta_i|. */
  readonly angleMax: number;
}

/** World-frame pose and position of a single tree node. */
export interface TreeNodePose {
  readonly frame: SE3;
  readonly position: Vec3;
}

/** Output of forwardKinematicsTree. */
export interface TreeKinematicsResult {
  readonly nodes: readonly TreeNodePose[];
  /** (nNodes,) world positions of each node. */
  readonly positions: readonly Vec3[];
}

// ---- Public API ----

/**
 * Construct a path-graph TreeStrip with uniform cell lengths.
 * Path graph: node 0 is root, node i's parent is i-1 for i > 0.
 *
 * @param nNodes - Number of nodes (>= 2).
 * @param cellLength - Uniform edge length (default 1).
 * @param angleMax - Hinge angle limit in radians (default pi).
 * @returns TreeStrip representing the path graph P_{nNodes}.
 */
export function pathGraphTree(nNodes: number, cellLength = 1, angleMax = Math.PI): TreeStrip {
  if (!Number.isInteger(nNodes) || nNodes < 2) {
    throw new Error(`pathGraphTree: nNodes must be an integer >= 2 (got ${nNodes})`);
  }
  if (!(cellLength > 0) || !Number.isFinite(cellLength)) {
    throw new Error(`pathGraphTree: cellLength must be positive finite (got ${cellLength})`);
  }
  if (!(angleMax > 0) || angleMax > Math.PI) {
    throw new Error(`pathGraphTree: angleMax must be in (0, π] (got ${angleMax})`);
  }
  const parents: (number | null)[] = [null, ...Array.from({ length: nNodes - 1 }, (_, i) => i)];
  const edgeLengths: number[] = Array.from({ length: nNodes - 1 }, () => cellLength);
  return { nNodes, parents, edgeLengths, angleMax };
}

/**
 * Forward kinematics for a tree strip.
 *
 * Traverses the tree by DFS from the root (node 0), accumulating SE(3)
 * transforms.  Node i's world pose is the composition of all ancestor
 * edge transforms along the path from root to i.
 *
 * @param tree - TreeStrip configuration.
 * @param thetas - Hinge angles, length = nNodes - 1 (one per non-root node).
 *                 Ordering: theta[i-1] is the angle at the edge from
 *                 parent[i] to node i (same indexing as edgeLengths).
 * @returns TreeKinematicsResult with world-frame poses and positions.
 * @throws Error if thetas length disagrees with nNodes - 1.
 */
export function forwardKinematicsTree(
  tree: TreeStrip,
  thetas: readonly number[],
): TreeKinematicsResult {
  if (thetas.length !== tree.nNodes - 1) {
    throw new Error(
      `forwardKinematicsTree: expected ${tree.nNodes - 1} hinge angles, got ${thetas.length}`,
    );
  }

  // Build adjacency list (parent → children).
  const children: number[][] = Array.from({ length: tree.nNodes }, () => []);
  for (let i = 1; i < tree.nNodes; i++) {
    const p = tree.parents[i];
    if (p === null || p === undefined) {
      throw new Error(`forwardKinematicsTree: non-root node ${i} has null parent`);
    }
    children[p]!.push(i);
  }

  const frames: SE3[] = new Array(tree.nNodes).fill(SE3_IDENTITY);
  const positions: Vec3[] = new Array(tree.nNodes);

  // DFS from root.
  const stack: number[] = [0];
  frames[0] = SE3_IDENTITY;
  positions[0] = se3Apply(SE3_IDENTITY, [0, 0, 0]);

  while (stack.length > 0) {
    const node = stack.pop()!;
    const frame = frames[node]!;
    positions[node] = se3Apply(frame, [0, 0, 0]);

    for (const child of children[node]!) {
      // theta index is child - 1 (root has no incoming edge).
      const theta = thetas[child - 1] ?? 0;
      const L = tree.edgeLengths[child - 1] ?? 0;
      const axis: Vec3 =
        tree.hingeAxes !== undefined ? (tree.hingeAxes[child - 1] ?? CELL_Y_AXIS) : CELL_Y_AXIS;
      // Compose: translate along L then rotate about hinge axis.
      const childFrame = se3Compose(frame, se3Compose(trans([L, 0, 0]), rot(axis, theta)));
      frames[child] = childFrame;
      stack.push(child);
    }
  }

  const nodes: TreeNodePose[] = Array.from({ length: tree.nNodes }, (_, i) => ({
    frame: frames[i]!,
    position: positions[i]!,
  }));

  return { nodes, positions };
}
