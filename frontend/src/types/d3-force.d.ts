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

  export interface SimulationLinkDatum<NodeDatum extends SimulationNodeDatum> {
    source: string | number | NodeDatum;
    target: string | number | NodeDatum;
    index?: number;
  }

  export function forceSimulation<NodeDatum extends SimulationNodeDatum>(
    nodes?: NodeDatum[],
  ): Simulation<NodeDatum, undefined>;

  export interface Simulation<NodeDatum extends SimulationNodeDatum, LinkDatum extends SimulationLinkDatum<NodeDatum> | undefined = undefined> {
    stop(): this;
    tick(): this;
    force(name: string, force: unknown): this;
    alpha(value: number): this;
    alphaTarget(value: number): this;
    alphaDecay(value: number): this;
    velocityDecay(value: number): this;
    restart(): this;
    on(typenames: string, listener: () => void): this;
  }

  export function forceLink<NodeDatum extends SimulationNodeDatum, Link extends SimulationLinkDatum<NodeDatum>>(
    links?: Link[],
  ): ForceLink<NodeDatum, Link>;

  export interface ForceLink<NodeDatum extends SimulationNodeDatum, Link extends SimulationLinkDatum<NodeDatum>> {
    id(
      accessor: (node: NodeDatum, index: number, nodes: NodeDatum[]) => string | number,
    ): this;
    distance(accessor: number | ((link: Link, index: number, links: Link[]) => number)): this;
    strength(accessor: number | ((link: Link, index: number, links: Link[]) => number)): this;
  }

  export function forceManyBody<NodeDatum extends SimulationNodeDatum>(): ForceManyBody<NodeDatum>;

  export interface ForceManyBody<NodeDatum extends SimulationNodeDatum> {
    strength(strength: number | ((node: NodeDatum, index: number, nodes: NodeDatum[]) => number)): this;
    distanceMax(distance: number): this;
  }

  export function forceCollide<NodeDatum extends SimulationNodeDatum>(): ForceCollide<NodeDatum>;

  export interface ForceCollide<NodeDatum extends SimulationNodeDatum> {
    radius(radius: number | ((node: NodeDatum, index: number, nodes: NodeDatum[]) => number)): this;
    strength(strength: number): this;
  }

  export function forceCenter(x?: number, y?: number): { x(x: number): void; y(y: number): void };

  export function forceX<NodeDatum extends SimulationNodeDatum>(x?: number | ((node: NodeDatum) => number)): ForcePosition<NodeDatum>;
  export function forceY<NodeDatum extends SimulationNodeDatum>(y?: number | ((node: NodeDatum) => number)): ForcePosition<NodeDatum>;

  export interface ForcePosition<NodeDatum extends SimulationNodeDatum> {
    strength(strength: number | ((node: NodeDatum, index: number, nodes: NodeDatum[]) => number)): this;
  }
}
