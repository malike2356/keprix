declare module "d3-force" {
  export interface SimulationNodeDatum {
    index?: number;
    x?: number;
    y?: number;
    vx?: number;
    vy?: number;
    fx?: number | null;
    fy?: number | null;
  }

  export function forceSimulation<NodeDatum extends SimulationNodeDatum>(
    nodes?: NodeDatum[],
  ): Simulation<NodeDatum>;

  export interface Simulation<NodeDatum extends SimulationNodeDatum> {
    stop(): this;
    tick(): this;
    force(name: string, force: unknown): this;
  }

  export function forceLink<Link, NodeDatum extends SimulationNodeDatum>(
    links?: Link[],
  ): ForceLink<Link, NodeDatum>;

  export interface ForceLink<Link, NodeDatum extends SimulationNodeDatum> {
    id(
      accessor: (node: NodeDatum, index: number, nodes: NodeDatum[]) => string | number,
    ): this;
    distance(accessor: number | ((link: Link, index: number, links: Link[]) => number)): this;
    strength(accessor: number | ((link: Link, index: number, links: Link[]) => number)): this;
  }

  export function forceManyBody<NodeDatum extends SimulationNodeDatum>(): ForceManyBody<NodeDatum>;

  export interface ForceManyBody<NodeDatum extends SimulationNodeDatum> {
    strength(strength: number | ((node: NodeDatum, index: number, nodes: NodeDatum[]) => number)): this;
  }

  export function forceCollide<NodeDatum extends SimulationNodeDatum>(): ForceCollide<NodeDatum>;

  export interface ForceCollide<NodeDatum extends SimulationNodeDatum> {
    radius(radius: number | ((node: NodeDatum, index: number, nodes: NodeDatum[]) => number)): this;
  }

  export function forceCenter(x?: number, y?: number): { x(x: number): void; y(y: number): void };
}
