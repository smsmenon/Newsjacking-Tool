'use client';

import { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Network, RefreshCw, Info } from 'lucide-react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useKnowledgeGraph } from '@/lib/api';
import type { Entity, EntityType } from '@/lib/types';
import { cn } from '@/lib/utils';

// ─── Entity colors ────────────────────────────────────────────

const ENTITY_COLORS: Record<EntityType, { bg: string; border: string; text: string }> = {
  company:    { bg: '#6366f1', border: '#818cf8', text: '#fff' },
  person:     { bg: '#06b6d4', border: '#22d3ee', text: '#fff' },
  technology: { bg: '#22c55e', border: '#4ade80', text: '#fff' },
  market:     { bg: '#f97316', border: '#fb923c', text: '#fff' },
  trend:      { bg: '#a855f7', border: '#c084fc', text: '#fff' },
  product:    { bg: '#eab308', border: '#facc15', text: '#000' },
};

// ─── Custom Entity Node ───────────────────────────────────────

function EntityNode({ data }: { data: { entity: Entity } }) {
  const { entity } = data;
  const colors = ENTITY_COLORS[entity.type] ?? ENTITY_COLORS.company;

  return (
    <div
      className="rounded-lg px-3 py-2 text-center shadow-elevated"
      style={{
        background: `${colors.bg}20`,
        border: `1px solid ${colors.border}`,
        minWidth: 100,
        maxWidth: 160,
      }}
    >
      <Handle type="target" position={Position.Top}    style={{ background: colors.border }} />
      <p className="text-[9px] font-semibold uppercase mb-0.5" style={{ color: colors.border }}>
        {entity.type}
      </p>
      <p className="text-xs font-bold text-white leading-tight line-clamp-2">{entity.name}</p>
      <p className="text-[9px] mt-0.5" style={{ color: colors.border }}>
        {entity.mentionCount} mentions
      </p>
      <Handle type="source" position={Position.Bottom} style={{ background: colors.border }} />
    </div>
  );
}

const nodeTypes: NodeTypes = { entity: EntityNode };

// ─── Convert graph data to React Flow ────────────────────────

function buildGraphElements(
  entities: Entity[],
  relationships: ReturnType<typeof useKnowledgeGraph>['data'] extends undefined ? never : NonNullable<ReturnType<typeof useKnowledgeGraph>['data']>['relationships']
): { nodes: Node[]; edges: Edge[] } {
  // Position nodes in a radial layout
  const nodeCount = entities.length;
  const radius    = Math.max(200, nodeCount * 30);
  const cx        = 600;
  const cy        = 400;

  const nodes: Node[] = entities.map((entity, i) => {
    const angle = (2 * Math.PI * i) / nodeCount;
    return {
      id:       entity.id,
      type:     'entity',
      position: {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
      },
      data: { entity },
    };
  });

  const edges: Edge[] = relationships.map((rel) => ({
    id:           rel.id,
    source:       rel.sourceEntityId,
    target:       rel.targetEntityId,
    label:        rel.relationshipType,
    animated:     rel.weight > 0.7,
    style:        { stroke: '#21262d', strokeWidth: Math.max(1, rel.weight * 3) },
    labelStyle:   { fill: '#8b949e', fontSize: 9 },
    labelBgStyle: { fill: '#161b22', fillOpacity: 0.9 },
  }));

  return { nodes, edges };
}

// ─── Entity Type Filter ───────────────────────────────────────

const ALL_TYPES: EntityType[] = ['company', 'person', 'technology', 'market', 'trend', 'product'];

// ─── Page ────────────────────────────────────────────────────

export default function GraphPage() {
  const [selectedTypes, setSelectedTypes] = useState<EntityType[]>([...ALL_TYPES]);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);

  const { data: graphData, isLoading, mutate: refetch } = useKnowledgeGraph(
    selectedTypes.length < ALL_TYPES.length ? selectedTypes : undefined
  );

  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!graphData) return { nodes: [], edges: [] };
    return buildGraphElements(graphData.entities, graphData.relationships);
  }, [graphData]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedEntity((node.data as { entity: Entity }).entity);
  }, []);

  const toggleType = (type: EntityType) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Network className="h-6 w-6 text-accent-400" />
            Knowledge Graph
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Visual map of entities and relationships extracted from intelligence
            {graphData && ` · ${graphData.entities.length} entities, ${graphData.relationships.length} connections`}
          </p>
        </div>
        <button onClick={() => refetch()}
          className="flex items-center gap-2 rounded-md border border-surface-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-brand-500/40 transition-colors">
          <RefreshCw className="h-3 w-3" />
          Refresh
        </button>
      </div>

      {/* Type Filter */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-muted-foreground">Filter by type:</span>
        {ALL_TYPES.map((type) => {
          const colors = ENTITY_COLORS[type];
          const active = selectedTypes.includes(type);
          return (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className={cn(
                'rounded-full px-3 py-1 text-[10px] font-semibold capitalize transition-all border',
                active ? 'opacity-100' : 'opacity-30'
              )}
              style={{
                background: active ? `${colors.bg}20` : 'transparent',
                borderColor: active ? colors.border : '#21262d',
                color: active ? colors.border : '#8b949e',
              }}
            >
              {type}
            </button>
          );
        })}
      </div>

      {/* Graph + Detail Panel */}
      <div className="flex flex-1 gap-4 min-h-0">
        {/* React Flow */}
        <div className="flex-1 rounded-lg border border-surface-border overflow-hidden">
          {isLoading ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center space-y-2">
                <Network className="h-8 w-8 text-muted-foreground mx-auto animate-pulse" />
                <p className="text-sm text-muted-foreground">Loading knowledge graph…</p>
              </div>
            </div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={handleNodeClick}
              fitView
              attributionPosition="bottom-left"
            >
              <Background color="#21262d" gap={24} size={1} />
              <Controls />
              <MiniMap
                nodeColor={(node) => {
                  const entity = (node.data as { entity: Entity })?.entity;
                  return entity ? ENTITY_COLORS[entity.type]?.bg ?? '#6366f1' : '#6366f1';
                }}
                style={{ background: '#161b22', border: '1px solid #21262d' }}
              />
            </ReactFlow>
          )}
        </div>

        {/* Entity Detail Panel */}
        {selectedEntity && (
          <motion.aside
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="w-64 shrink-0 rounded-lg border border-surface-border bg-surface-elevated p-4 space-y-4 overflow-y-auto scrollbar-thin"
          >
            <div className="flex items-start justify-between">
              <div>
                <span
                  className="rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize"
                  style={{
                    background: `${ENTITY_COLORS[selectedEntity.type].bg}20`,
                    color: ENTITY_COLORS[selectedEntity.type].border,
                    border: `1px solid ${ENTITY_COLORS[selectedEntity.type].border}`,
                  }}
                >
                  {selectedEntity.type}
                </span>
                <h3 className="font-semibold text-foreground mt-2">{selectedEntity.name}</h3>
              </div>
              <button onClick={() => setSelectedEntity(null)} className="text-muted-foreground hover:text-foreground">
                ×
              </button>
            </div>

            {selectedEntity.description && (
              <p className="text-xs text-muted-foreground">{selectedEntity.description}</p>
            )}

            <div className="space-y-2 text-[11px]">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Mentions</span>
                <span className="font-mono font-bold text-brand-400">{selectedEntity.mentionCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">First seen</span>
                <span className="text-foreground">{new Date(selectedEntity.firstSeen).toLocaleDateString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Last seen</span>
                <span className="text-foreground">{new Date(selectedEntity.lastSeen).toLocaleDateString()}</span>
              </div>
            </div>

            {Object.keys(selectedEntity.properties).length > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Properties</p>
                <div className="space-y-1">
                  {Object.entries(selectedEntity.properties).slice(0, 5).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-[11px]">
                      <span className="text-muted-foreground capitalize">{k}</span>
                      <span className="text-foreground font-medium truncate max-w-24">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.aside>
        )}
      </div>
    </div>
  );
}
