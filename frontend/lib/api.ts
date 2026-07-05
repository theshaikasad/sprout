export const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Citation = {
  video_id: string;
  title: string;
  channel: string;
  views: number;
  published: string;
};

export type Trace = {
  trend: string;
  topics: string[];
  videos: string[];
  formats: string[];
  hooks: string[];
};

export type Card = {
  title: string;
  title_variants?: string[];
  angle: string;
  hook: { text: string; style: string };
  format: string;
  outline: string[];
  why: string;
  topic_labels_used: string[];
  cited_video_ids: string[];
  broll_keywords?: string[];
  thumbnail?: { concept: string; overlay_text: string };
  citations: Citation[];
  trace: Trace;
};

export type SuggestResponse = { trend: string; cards: Card[]; error?: string };

export type EvidenceVideo = {
  video_id: string;
  title: string;
  channel: string | null;
  views: number;
  published: string;
  fit?: "strong" | "stretch" | "skip";
};

export type Trend = {
  node_id: string;
  label: string;
  peaked_at: string;
  evidence: number;
  evidence_videos: EvidenceVideo[];
};

export type LibraryVideo = {
  video_id: string;
  title: string;
  published: string;
  views: number;
  ratio: number;
  format: string | null;
  topics: string[];
  channel: string | null;
};

export type Library = {
  creator: {
    handle: string;
    title: string;
    avatar: string;
    subscribers: number;
    video_count: number;
  };
  holdout_cutoff: string;
  live_videos: LibraryVideo[];
  holdout_count: number;
  competitors: {
    handle: string;
    title: string;
    avatar: string;
    subscribers: number;
    videos: LibraryVideo[];
  }[];
  trend_videos: LibraryVideo[];
};

export type GraphNode = {
  id: string;
  type: "Video" | "Topic" | "Hook" | "Format" | "Creator" | "Trend";
  label: string;
  node_sets: string[];
  views: number | null;
  feedback_weight: number;
};

export type GraphEdge = { source: string; target: string; rel: string };

export type GraphData = { nodes: GraphNode[]; edges: GraphEdge[] };

export type HoldoutVideo = {
  video_id: string;
  title: string;
  published: string;
  views: number;
  ratio_vs_baseline: number;
  topics: string[];
  format: string | null;
  hook_style: string | null;
};

export type BacktestMatch = {
  card_index: number;
  card_title: string;
  holdout_video: string;
  holdout_video_id?: string;
  holdout_views: number;
  ratio_vs_baseline: number;
  shared_topics: string[];
  alignment_score?: number;
};

export type BacktestResponse = {
  holdout_cutoff: string;
  proof_trend: string;
  champion: HoldoutVideo | null;
  best_match: BacktestMatch | null;
  suggested: SuggestResponse;
  holdout_reveal: HoldoutVideo[];
  matches: BacktestMatch[];
};

export type GapFinderResult = {
  topic_id: string;
  label: string;
  belongs_to_set: string[];
  distance_to_niche: number;
};

export type ContrastResponse = {
  query: string;
  trend: string;
  rag: { mode: string; query: string; chunks_used: number; answer: string };
  graph: {
    mode: string;
    cards: Array<{
      title: string;
      hook: { text: string; style: string };
      format: string;
      why: string;
      citations: Citation[];
    }>;
    headline_card: Card | null;
  };
  gap_finder: {
    mode: string;
    cypher_query: string;
    raw_match_count: number;
    gaps: GapFinderResult[];
  };
};


export type Evidence = { point: string; video_id: string };

export type Review = {
  verdict: string;
  confidence: number;
  fit: string;
  evidence_for: Evidence[];
  evidence_against: Evidence[];
  collisions: Evidence[];
  recommended: { title: string; hook: { text: string; style: string }; format: string };
  cited_video_ids: string[];
  citations: Citation[];
  trace: Trace;
};

export type Draft = {
  id: string;
  title: string;
  angle?: string;
  format_name?: string;
  state: "seed" | "planted" | "sprouted";
  topic_labels?: string[];
  concept_art_path?: string;
  production_kit_ready?: boolean;
  created_at?: string;
  planted_at?: string;
  sprouted_at?: string;
};

export type ProductionKitReceipt = {
  pattern_label?: string;
  confidence?: string;
  support_n?: number;
  effect_size?: number;
  metric?: string;
  type?: string;
  note?: string;
  video_id?: string;
  title?: string;
  ctr?: number;
};

export type ProductionKit = {
  idea_id: string;
  generated_at: string;
  thumbnail_brief: {
    overlay_text: string;
    overlay_word_count: number;
    composition: {
      layout: string;
      subject_placement: string;
      expression: string;
      contrast_direction: string;
      face_in_frame: boolean;
      text_zone: string;
    };
    designer_notes: string;
    precedents: {
      video_id: string;
      title: string;
      ctr: number;
      packaging: Record<string, unknown>;
    }[];
    receipts: ProductionKitReceipt[];
  };
  script_skeleton: {
    format: string;
    is_short: boolean;
    total_target_sec: number;
    total_target: string;
    beats: {
      type: string;
      start_sec: number;
      end_sec: number;
      time_range: string;
      target_duration_sec: number;
      line: string;
      guidance: string;
      receipts: ProductionKitReceipt[];
    }[];
  };
};

export type Plant = {
  video_id: string;
  title: string;
  published: string;
  views: number;
  ratio?: number;
  from_idea?: boolean;
  draft_id?: string;
};

export type Garden = {
  consistency: {
    days_since_last: number | null;
    median_gap_days?: number;
    momentum_weeks: number;
    encouragement: string;
  };
  planted: Draft[];
  seeds: Draft[];
  plants: Plant[];
  genre: { label?: string; summary?: string; dominant_format?: string };
};

export type Idea = Draft & {
  created?: string;
  status?: "saved" | "scripting" | "filming" | "posted";
  source?: string;
  target?: string | null;
  payload?: Record<string, unknown>;
};

export type Cadence = {
  days_since_last: number | null;
  median_gap_days?: number;
  last_published?: string;
  overdue?: boolean;
};

export type TrackedUpload = {
  video_id: string;
  title: string;
  published: string;
  age_days: number;
  views: number;
  views_delta: number;
  ratio: number;
  projected_ratio: number;
  status: "above" | "on_track" | "under";
  improved: boolean;
};

export type Track = {
  checked_at: number;
  median_views: number;
  uploads: TrackedUpload[];
  improved_nodes: number;
  improved_labels?: string[];
};

export type PulseItem = {
  source: string;
  title: string;
  url: string;
  score?: number;
  fit?: number;
};

export type Pulse = {
  generated_at?: string;
  niche?: string;
  items: PulseItem[];
};

async function authHeaders(): Promise<Record<string, string>> {
  const h: Record<string, string> = { "content-type": "application/json" };
  try {
    const { getIdToken } = await import("./firebase");
    const token = await getIdToken();
    if (token) h.Authorization = `Bearer ${token}`;
  } catch {
    /* demo mode */
  }
  return h;
}

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...headers, ...init?.headers },
  });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

export const api = {
  trends: () => j<Trend[]>("/trends"),
  library: () => j<Library>("/library"),
  review: (idea: string) =>
    j<Review>("/review", { method: "POST", body: JSON.stringify({ idea }) }),
  garden: () => j<Garden>("/garden"),
  fingerprint: () => j<{ genre: Garden["genre"]; competitors: unknown[] }>("/fingerprint"),
  ideas: () => j<Idea[]>("/ideas"),
  plantIdea: (id: string) => j<Draft>(`/ideas/${id}/plant`, { method: "POST" }),
  productionKit: (id: string) => j<ProductionKit>(`/ideas/${id}/production-kit`),
  patterns: () => j<{ patterns: unknown[] }>("/patterns"),
  addIdea: (title: string, source: string, payload: object, target?: string) =>
    j<Idea>("/ideas", {
      method: "POST",
      body: JSON.stringify({ title, source, payload, target }),
    }),
  patchIdea: (id: string, patch: { status?: string; target?: string }) =>
    j<Idea>(`/ideas/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  deleteIdea: (id: string) => j<{ ok: boolean }>(`/ideas/${id}`, { method: "DELETE" }),
  cadence: () => j<Cadence>("/cadence"),
  track: () => j<Track>("/track"),
  pulse: () => j<Pulse>("/pulse"),
  connect: (handle?: string) =>
    j<{ ok: boolean; channel: { title: string; avatar: string; subscribers: number } | null }>(
      "/connect",
      { method: "POST", body: JSON.stringify({ handle: handle ?? "" }) },
    ),
  onboardingStart: () =>
    j<{ ok: boolean; status: string }>("/onboarding/start", { method: "POST" }),
  onboardingNiche: (niche: string) =>
    j<{ ok: boolean; declared_niche: string }>("/onboarding/niche", {
      method: "POST",
      body: JSON.stringify({ niche }),
    }),
  onboardingStatus: () =>
    j<{
      stage: string;
      detail: string;
      status: string;
      error: string;
      elapsed?: number;
      channel_video_count?: number;
      preview_tier?: "empty" | "warming" | "established";
      needs_niche?: boolean;
      declared_niche?: string;
      use_backtest_reveal?: boolean;
      cold_start?: {
        tier: string;
        live_video_count: number;
        patterns_enabled: boolean;
        niche_query?: string;
      };
      genre?: { label?: string; summary?: string; dominant_format?: string };
      channel: {
        title: string;
        avatar: string;
        subscribers: number;
        handle?: string;
        video_count?: number;
      } | null;
    }>("/onboarding/status"),
  youtubeAuthUrl: () => j<{ url: string }>("/auth/youtube/url"),
  telegramLink: () =>
    j<{
      url: string;
      start_command: string;
      token: string;
      bot_username: string;
    }>("/telegram/link"),
  telegramStatus: () => j<{ linked: boolean; chat_id_masked: string }>("/telegram/status"),
  connectStatus: () =>
    j<{
      stage: "idle" | "fetching" | "enriching" | "ingesting" | "done" | "error";
      detail: string;
      handle: string;
      channel: { title: string; avatar: string; subscribers: number } | null;
      elapsed: number;
      error: string;
    }>("/connect/status"),
  suggest: (trend?: string) =>
    j<SuggestResponse>(`/suggest${trend ? `?trend=${encodeURIComponent(trend)}` : ""}`),
  graph: () => j<GraphData>("/graph"),
  feedback: (trace: Trace, performance_pct: number) =>
    j<{ updated: Record<string, number> }>("/feedback", {
      method: "POST",
      body: JSON.stringify({ trace, performance_pct }),
    }),
  decay: (trend: string) =>
    j<{ deleted_nodes: number }>("/decay", {
      method: "POST",
      body: JSON.stringify({ trend }),
    }),
  chat: (message: string, history: { role: string; content: string }[]) =>
    j<{ reply: string; tool_calls: { tool: string; args: Record<string, unknown> }[] }>(
      "/chat",
      { method: "POST", body: JSON.stringify({ message, history }) },
    ),
  backtest: (trend?: string) =>
    j<BacktestResponse>(
      `/backtest${trend ? `?trend=${encodeURIComponent(trend)}` : ""}`,
    ),
  contrast: (trend?: string) =>
    j<ContrastResponse>(
      `/contrast${trend ? `?trend=${encodeURIComponent(trend)}` : ""}`,
    ),
  gaps: (niche?: string) =>
    j<{ cypher_query: string; raw_match_count: number; gaps: GapFinderResult[] }>(
      `/gaps${niche ? `?niche=${encodeURIComponent(niche)}` : ""}`,
    ),
  telegramSend: (message?: string, uid?: string) =>
    j<{ sent: boolean; text: string; uid: string; chat_id: string | null; configured: boolean }>(
      "/telegram/send",
      {
        method: "POST",
        body: JSON.stringify({ ...(message ? { message } : {}), ...(uid ? { uid } : {}) }),
      },
    ),
  telegramPoll: () =>
    j<{ processed: unknown[]; configured: boolean }>("/telegram/poll"),
};
