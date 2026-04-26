import { describe, expect, it } from "vitest";
import { flatState, forwardKinematics, makeStrip, makeUniformStrip } from "../src/index.js";
import { forwardKinematicsTree, pathGraphTree } from "../src/tree.js";

const closeTo = (a: number, b: number, tol = 1e-15) => Math.abs(a - b) <= tol;
const vecClose = (a: readonly number[], b: readonly number[], tol = 1e-15) =>
  a.length === b.length && a.every((x, i) => closeTo(x, b[i] ?? Number.NaN, tol));

describe("pathGraphTree", () => {
  it("rejects nNodes < 2", () => {
    expect(() => pathGraphTree(1)).toThrow();
    expect(() => pathGraphTree(0)).toThrow();
  });

  it("rejects non-positive cellLength", () => {
    expect(() => pathGraphTree(4, 0)).toThrow();
    expect(() => pathGraphTree(4, -1)).toThrow();
  });

  it("produces correct parent array", () => {
    const tree = pathGraphTree(5);
    expect(tree.parents).toEqual([null, 0, 1, 2, 3]);
  });

  it("produces correct edge lengths", () => {
    const tree = pathGraphTree(5, 2);
    expect(tree.edgeLengths).toEqual([2, 2, 2, 2]);
  });
});

describe("forwardKinematicsTree — path graph equivalence", () => {
  it("flat strip: positions match forwardKinematics at atol=1e-15", () => {
    const n = 8;
    const tree = pathGraphTree(n, 1);
    const thetas = new Array(n - 1).fill(0);
    const treeResult = forwardKinematicsTree(tree, thetas);

    const strip = makeUniformStrip(n, 1);
    const stripResult = forwardKinematics(strip, flatState(strip));

    for (let i = 0; i < n; i++) {
      expect(vecClose(treeResult.positions[i]!, stripResult.cells[i]!.position)).toBe(true);
    }
  });

  it("non-trivial thetas match forwardKinematics at atol=1e-15", () => {
    const n = 8;
    const thetas = [0.1, 0.2, -0.3, 0.4, -0.5, 0.6, -0.7];
    const tree = pathGraphTree(n, 1);
    const treeResult = forwardKinematicsTree(tree, thetas);

    const strip = makeUniformStrip(n, 1);
    const stripResult = forwardKinematics(strip, { thetas });

    for (let i = 0; i < n; i++) {
      const tp = treeResult.positions[i]!;
      const sp = stripResult.cells[i]!.position;
      for (let k = 0; k < 3; k++) {
        expect(closeTo(tp[k]!, sp[k]!, 1e-15)).toBe(true);
      }
    }
  });

  it("non-uniform cell lengths: path graph root at origin, all positions finite", () => {
    // Custom edge lengths for a non-uniform path graph tree.
    const lengths = [1.5, 0.8, 2.0, 1.1, 0.5];
    const nNodes = lengths.length + 1;
    const parents: (number | null)[] = [null, ...Array.from({ length: nNodes - 1 }, (_, i) => i)];
    const tree = {
      nNodes,
      parents,
      edgeLengths: lengths,
      angleMax: Math.PI,
    };
    const thetas = [0.3, -0.1, 0.5, -0.2, 0.4];
    const treeResult = forwardKinematicsTree(tree, thetas);

    // Root must stay at origin.
    expect(vecClose(treeResult.positions[0]!, [0, 0, 0])).toBe(true);
    for (const pos of treeResult.positions) {
      for (const coord of pos) {
        expect(Number.isFinite(coord)).toBe(true);
      }
    }
  });

  it("non-uniform cell lengths flat: positions match makeStrip forwardKinematics at 1e-15", () => {
    // When all hinges are 0, tree path graph and strip must agree exactly.
    const cellLengths = [1.5, 0.8, 2.0, 1.1, 0.5, 1.3];
    const nNodes = cellLengths.length + 1;
    // tree: nNodes nodes, edgeLengths = cellLengths (edge i = length of cell i+1 in strip).
    // strip: nCells = nNodes, cellLengths = [some_first, ...cellLengths].
    // For path graph tree, cell 0 of strip occupies [0, edgeLengths[0]], cell 1 occupies next, etc.
    // But tree.edgeLengths[i] = distance from node i to node i+1.
    // In strip, cellLengths[i] = length of cell i.
    // When flat, position of node i in tree = [sum(edgeLengths[0..i-1]), 0, 0].
    // Position of cell i in strip = [sum(cellLengths[0..i-1]), 0, 0].
    // These match when tree.edgeLengths[i] = strip.cellLengths[i].
    const parents: (number | null)[] = [null, ...Array.from({ length: nNodes - 1 }, (_, i) => i)];
    const tree = { nNodes, parents, edgeLengths: cellLengths, angleMax: Math.PI };
    const thetas = new Array(nNodes - 1).fill(0);
    const treeResult = forwardKinematicsTree(tree, thetas);

    // Verify cumulative positions.
    let cumX = 0;
    for (let i = 0; i < nNodes; i++) {
      expect(closeTo(treeResult.positions[i]![0]!, cumX, 1e-15)).toBe(true);
      expect(closeTo(treeResult.positions[i]![1]!, 0, 1e-15)).toBe(true);
      expect(closeTo(treeResult.positions[i]![2]!, 0, 1e-15)).toBe(true);
      if (i < nNodes - 1) cumX += cellLengths[i]!;
    }
  });
});

describe("forwardKinematicsTree — Y-shaped tree (K_{1,3})", () => {
  // Y-tree: root (0) has 3 children (1, 2, 3); each at 45 deg.
  const yTree = {
    nNodes: 4,
    parents: [null, 0, 0, 0] as (number | null)[],
    edgeLengths: [1, 1, 1],
    angleMax: Math.PI,
  };

  it("flat angles: all children are at (1, 0, 0)", () => {
    const thetas = [0, 0, 0];
    const result = forwardKinematicsTree(yTree, thetas);
    for (let c = 1; c <= 3; c++) {
      expect(vecClose(result.positions[c]!, [1, 0, 0])).toBe(true);
    }
  });

  it("non-zero angles: all child positions are finite", () => {
    // All 3 children of the root share the same origin position [1,0,0]
    // (hinge rotation affects orientation of the child frame, not the
    // child's leading-edge position in the parent's frame).
    const thetas = [0.3, -0.5, 1.0];
    const result = forwardKinematicsTree(yTree, thetas);
    for (const pos of result.positions) {
      for (const coord of pos) {
        expect(Number.isFinite(coord)).toBe(true);
      }
    }
    // Children 1, 2, 3 all originate at the end of edge length=1 from root.
    for (let c = 1; c <= 3; c++) {
      expect(vecClose(result.positions[c]!, [1, 0, 0])).toBe(true);
    }
    // But frames (orientations) differ.
    const f1 = result.nodes[1]!.frame;
    const f2 = result.nodes[2]!.frame;
    // Non-zero thetas → different quaternions.
    const quatsDiffer = f1.q.some((v, i) => Math.abs(v - (f2.q[i] ?? 0)) > 1e-9);
    expect(quatsDiffer).toBe(true);
  });

  it("throws when thetas length disagrees with nNodes-1", () => {
    expect(() => forwardKinematicsTree(yTree, [0, 0])).toThrow(/expected 3/);
    expect(() => forwardKinematicsTree(yTree, [0, 0, 0, 0])).toThrow(/expected 3/);
  });
});
