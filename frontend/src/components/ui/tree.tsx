import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

export type TreeNode<T> = T;

export interface TreeProps<T> {
  nodes: T[];
  getId: (n: T) => string;
  getChildren: (n: T) => T[];
  renderNode: (n: T) => ReactNode;
  expandedIds: Set<string>;
  onExpandChange: (next: Set<string>) => void;
  onSelect?: (n: T) => void;
  selectedId?: string | null;
}

export function Tree<T>(props: TreeProps<T>) {
  return (
    <ul className="flex flex-col gap-0.5" role="tree">
      {props.nodes.map((n) => (
        <TreeItem<T> key={props.getId(n)} node={n} depth={0} {...props} />
      ))}
    </ul>
  );
}

function TreeItem<T>(
  props: TreeProps<T> & { node: T; depth: number },
) {
  const {
    node,
    depth,
    getId,
    getChildren,
    renderNode,
    expandedIds,
    onExpandChange,
    onSelect,
    selectedId,
  } = props;
  const id = getId(node);
  const children = getChildren(node);
  const hasChildren = children.length > 0;
  const isExpanded = expandedIds.has(id);
  const isSelected = selectedId === id;

  const toggle = () => {
    const next = new Set(expandedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onExpandChange(next);
  };

  return (
    <li role="treeitem" aria-expanded={hasChildren ? isExpanded : undefined}>
      <div
        className={cn(
          "flex items-center gap-2 rounded px-2 py-1 hover:bg-accent",
          isSelected && "bg-accent",
        )}
        style={{ paddingLeft: `${depth * 1.25 + 0.5}rem` }}
      >
        {hasChildren ? (
          <button
            type="button"
            aria-label={`${isExpanded ? "收起" : "展开"} ${
              typeof node === "object" && node !== null && "name" in (node as object)
                ? (node as unknown as { name: string }).name
                : id
            }`}
            onClick={toggle}
            className="inline-flex h-5 w-5 items-center justify-center text-xs text-muted-foreground"
          >
            {isExpanded ? "▾" : "▸"}
          </button>
        ) : (
          <span className="inline-block h-5 w-5" aria-hidden="true" />
        )}
        <button
          type="button"
          className="flex-1 truncate text-left"
          onClick={() => onSelect?.(node)}
        >
          {renderNode(node)}
        </button>
      </div>
      {hasChildren && isExpanded ? (
        <ul role="group" className="flex flex-col gap-0.5">
          {children.map((c) => (
            <TreeItem<T>
              key={getId(c)}
              {...props}
              node={c}
              depth={depth + 1}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}
