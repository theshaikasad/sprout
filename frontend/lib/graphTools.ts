/** Agent tools that traverse the Cognee memory graph (see agent.py TOOLS). */
export const GRAPH_TOOLS = new Set([
  "recall_suggestions",
  "check_competitors",
  "scan_trends",
  "confirm_pattern",
  "search_discourse",
  "forget_trend",
  "get_my_performance",
]);

export function touchesGraph(tools: string[]): boolean {
  return tools.some((t) => GRAPH_TOOLS.has(t));
}
