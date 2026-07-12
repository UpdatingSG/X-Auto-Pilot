/** Never use process.env here — it gets baked into the client bundle at build time. */
function getApiBaseUrl(): string {
  if (typeof window === "undefined") {
    return "";
  }
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    return "http://localhost:8000";
  }
  // Call Render directly from the browser to avoid Vercel rewrite timeouts (ROUTER_EXTERNAL_TARGET_ERROR).
  return "https://xautopilot-api.onrender.com";
}

export type User = {
  id: string;
  email: string;
  timezone: string;
  created_at: string;
};

export type VoiceProfile = {
  id: string;
  version: number;
  is_active: boolean;
  display_name: string | null;
  bio: string | null;
  profession: string | null;
  interests: { topic: string; weight: number }[];
  expertise: string[];
  writing_style: Record<string, string>;
  tone: string[];
  personality: string[];
  vocabulary: { use: string[]; avoid: string[] };
  favorite_creators?: { handle: string; note?: string }[];
  never_discuss: string[];
  audience_type: string | null;
  created_at: string;
};

export type KnowledgeSource = {
  id: string;
  source_type: string;
  name: string;
  config: Record<string, string>;
  is_enabled: boolean;
  last_fetched_at: string | null;
};

export type KnowledgeItem = {
  id: string;
  title: string;
  url: string | null;
  author: string | null;
  fetched_at: string;
};

export type FetchResult = {
  source_id: string;
  items_ingested: number;
  items_skipped: number;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  email?: string;
};

export type ContentIdea = {
  id: string;
  content_type: string;
  category: string;
  status: string;
  title: string;
  hook_idea: string | null;
  rationale: string | null;
  reply_target_id?: string | null;
};

export type ReplyTarget = {
  id: string;
  author_handle: string;
  tweet_text: string;
  x_tweet_id: string;
  x_user_id: string;
  relevance_score: number | null;
  discovered_at: string;
  expires_at: string | null;
  reply_allowed?: boolean;
  reply_block_reason?: string | null;
};

export type DiscoveredReplyTarget = {
  x_tweet_id: string;
  x_user_id: string;
  author_handle: string;
  tweet_text: string;
  author_followers: number;
  likes: number;
  relevance_score: number;
  reply_allowed?: boolean;
  reply_block_reason?: string | null;
};

export type PlanComposition = {
  tweets: number;
  threads: number;
  replies: number;
  quotes?: number;
  growth_mode?: boolean;
  thread_days: string[];
  is_thread_day: boolean;
  reply_targets_available: number;
  hints: string[];
};

export type ContentPlan = {
  id: string;
  plan_date: string;
  status: string;
  ideas: ContentIdea[];
  composition?: PlanComposition | null;
};

export type DraftVariant = {
  id: string;
  variant_index: number;
  content_text: string | null;
  thread_tweets?: { index: number; text: string }[] | null;
  scores: Record<string, number>;
  is_selected: boolean;
};

export type Draft = {
  id: string;
  idea_id: string | null;
  content_type: string;
  category: string | null;
  status: string;
  selected_variant_id: string | null;
  scheduled_at: string | null;
  variants: DraftVariant[];
};

export type PostingWindow = {
  start: string;
  end: string;
  days: number[];
};

export type Schedule = {
  id: string;
  tweets_per_day: number;
  threads_per_week: number;
  replies_per_day: number;
  quote_tweets_per_day: number;
  posting_windows: PostingWindow[];
  jitter_minutes: number;
  require_approval: boolean;
  is_active: boolean;
  growth_mode: boolean;
  auto_schedule_replies: boolean;
};

export type QueueItem = {
  draft_id: string;
  content_type: string;
  category: string | null;
  scheduled_at: string;
  preview_text: string | null;
  status: string;
};

export type XAccount = {
  id: string;
  x_user_id: string;
  handle: string;
  connected: boolean;
  is_active: boolean;
  needs_reauth: boolean;
};

export type PublishedPost = {
  id: string;
  draft_id: string;
  x_tweet_id: string;
  content_type: string;
  preview_text: string | null;
  status: string;
  published_at: string;
};

export type AnalyticsOverview = {
  period: string;
  posts_published: number;
  total_impressions: number;
  avg_engagement_rate: number;
  top_post: {
    post_id: string;
    preview_text: string | null;
    engagement_rate: number;
    impressions: number;
  } | null;
};

export type PostMetricsSnapshot = {
  impressions: number;
  likes: number;
  replies: number;
  reposts: number;
  bookmarks: number;
  quotes: number;
  engagement_rate: number;
  captured_at: string;
};

export type PostAnalyticsItem = {
  post_id: string;
  draft_id: string;
  x_tweet_id: string;
  preview_text: string | null;
  category: string | null;
  content_type?: string | null;
  published_at: string;
  metrics: PostMetricsSnapshot | null;
};

export type BriefingResponse = {
  date: string;
  growth_mode: boolean;
  targets: {
    replies_goal: number;
    replies_sent: number;
    tweets_goal: number;
    tweets_sent: number;
    threads_goal: number;
    threads_sent: number;
  };
  fresh_opportunities: {
    x_tweet_id: string;
    author_handle: string;
    tweet_text: string;
    author_followers: number;
    likes: number;
    relevance_score: number;
    source: string;
    reply_target_id?: string | null;
    has_draft?: boolean;
  }[];
  saved_targets: BriefingResponse["fresh_opportunities"];
  actions: { priority: string; action: string; detail: string }[];
  hints: string[];
  discovery_message?: string | null;
};

export type GrowthDashboard = {
  growth_mode: boolean;
  period: string;
  daily_targets: Record<string, number>;
  today_counts: Record<string, number>;
  week_counts: Record<string, number>;
  follower_delta_7d: number | null;
  content_breakdown: {
    content_type: string;
    count: number;
    avg_impressions: number;
    avg_engagement_rate: number;
    avg_bookmarks: number;
  }[];
  reply_performance: {
    post_id: string;
    preview_text: string | null;
    impressions: number;
    likes: number;
    replies: number;
    engagement_rate: number;
    published_at: string;
  }[];
  streak: { reply_days: number };
};

export type AnalyticsInsights = {
  period: string;
  what_worked: string[];
  what_failed: string[];
  best_posting_hour: number | null;
  best_category: string | null;
  recommended_adjustments: { increase_weight?: string[]; decrease_weight?: string[] };
};

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${getApiBaseUrl()}${path}`, { ...options, headers });

  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    let message = response.statusText;
    if (contentType.includes("application/json")) {
      const body = await response.json().catch(() => ({}));
      const detail = body.detail;
      message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: { msg?: string }) => d.msg).join(", ")
            : message;
    } else {
      const text = await response.text();
      if (text) message = text;
    }
    throw new ApiError(response.status, message || "Request failed");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string }>("/health"),

  register: (email: string, password: string) =>
    request<User>("/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: (token: string) => request<User>("/v1/auth/me", {}, token),

  getVoiceProfile: (token: string) =>
    request<VoiceProfile>("/v1/profile/voice", {}, token),

  saveVoiceProfile: (token: string, data: Record<string, unknown>) =>
    request<VoiceProfile>(
      "/v1/profile/voice",
      { method: "POST", body: JSON.stringify(data) },
      token,
    ),

  listSources: (token: string) => request<KnowledgeSource[]>("/v1/sources", {}, token),

  createSource: (token: string, data: Record<string, unknown>) =>
    request<KnowledgeSource>(
      "/v1/sources",
      { method: "POST", body: JSON.stringify(data) },
      token,
    ),

  fetchSource: (token: string, sourceId: string) =>
    request<FetchResult>(
      `/v1/sources/${sourceId}/fetch`,
      { method: "POST" },
      token,
    ),

  listKnowledgeItems: (token: string) =>
    request<KnowledgeItem[]>("/v1/knowledge/items", {}, token),

  getTodayPlan: (token: string) => request<ContentPlan>("/v1/plans/today", {}, token),

  generatePlan: (token: string, force = false) =>
    request<ContentPlan>(
      `/v1/plans/generate${force ? "?force=true" : ""}`,
      { method: "POST" },
      token,
    ),

  updateIdeaStatus: (token: string, planId: string, ideaId: string, status: string) =>
    request<ContentIdea>(
      `/v1/plans/${planId}/ideas/${ideaId}`,
      { method: "PATCH", body: JSON.stringify({ status }) },
      token,
    ),

  generateDraft: (token: string, ideaId: string) =>
    request<Draft>(
      "/v1/drafts/generate",
      { method: "POST", body: JSON.stringify({ idea_id: ideaId }) },
      token,
    ),

  listDrafts: (token: string, status?: string) =>
    request<Draft[]>(`/v1/drafts${status ? `?status=${status}` : ""}`, {}, token),

  approveDraft: (token: string, draftId: string, variantId: string) =>
    request<Draft>(
      `/v1/drafts/${draftId}`,
      {
        method: "PATCH",
        body: JSON.stringify({ status: "approved", selected_variant_id: variantId }),
      },
      token,
    ),

  rejectDraft: (token: string, draftId: string) =>
    request<Draft>(
      `/v1/drafts/${draftId}`,
      { method: "PATCH", body: JSON.stringify({ status: "rejected" }) },
      token,
    ),

  selectDraftVariant: (token: string, draftId: string, variantId: string) =>
    request<Draft>(
      `/v1/drafts/${draftId}`,
      { method: "PATCH", body: JSON.stringify({ selected_variant_id: variantId }) },
      token,
    ),

  getSchedule: (token: string) => request<Schedule>("/v1/schedule", {}, token),

  updateSchedule: (token: string, data: Partial<Schedule>) =>
    request<Schedule>(
      "/v1/schedule",
      { method: "PUT", body: JSON.stringify(data) },
      token,
    ),

  scheduleDraft: (token: string, draftId: string) =>
    request<Draft>(`/v1/drafts/${draftId}/schedule`, { method: "POST", body: "{}" }, token),

  cancelSchedule: (token: string, draftId: string) =>
    request<Draft>(`/v1/drafts/${draftId}/schedule`, { method: "DELETE" }, token),

  getPublishQueue: (token: string) => request<QueueItem[]>("/v1/publish/queue", {}, token),

  getXAccount: (token: string) => request<XAccount>("/v1/x/account", {}, token),

  connectXAccount: (token: string, handle: string) =>
    request<XAccount>(
      "/v1/x/account/connect",
      { method: "POST", body: JSON.stringify({ handle }) },
      token,
    ),

  getXConfig: (token: string) =>
    request<{ connection_mode: string }>("/v1/x/config", {}, token),

  startXOAuth: (token: string) =>
    request<{ authorization_url: string; state: string }>(
      "/v1/x/oauth/start",
      { method: "POST", body: "{}" },
      token,
    ),

  completeXOAuth: (token: string, code: string, state: string) =>
    request<XAccount>(
      "/v1/x/oauth/complete",
      { method: "POST", body: JSON.stringify({ code, state }) },
      token,
    ),

  disconnectXAccount: (token: string) =>
    request<void>("/v1/x/account", { method: "DELETE" }, token),

  publishDraft: (token: string, draftId: string) =>
    request<PublishedPost>(`/v1/publish/${draftId}`, { method: "POST", body: "{}" }, token),

  getPublishHistory: (token: string) => request<PublishedPost[]>("/v1/publish/history", {}, token),

  getAnalyticsOverview: (token: string, period = "7d") =>
    request<AnalyticsOverview>(`/v1/analytics/overview?period=${period}`, {}, token),

  getAnalyticsPosts: (token: string, period = "30d") =>
    request<PostAnalyticsItem[]>(`/v1/analytics/posts?period=${period}`, {}, token),

  syncPostMetrics: (token: string, postId: string) =>
    request<PostMetricsSnapshot>(
      `/v1/analytics/posts/${postId}/sync`,
      { method: "POST", body: "{}" },
      token,
    ),

  getAnalyticsInsights: (token: string) =>
    request<AnalyticsInsights>("/v1/analytics/insights", {}, token),

  listReplyTargets: (token: string) =>
    request<ReplyTarget[]>("/v1/reply-targets", {}, token),

  createReplyTarget: (
    token: string,
    data: { author_handle: string; tweet_text: string; x_tweet_id: string },
  ) =>
    request<ReplyTarget>(
      "/v1/reply-targets",
      { method: "POST", body: JSON.stringify(data) },
      token,
    ),

  discoverReplyTargets: (
    token: string,
    data?: { min_followers?: number; limit?: number; topics?: string[] },
  ) =>
    request<{ source: string; message?: string; targets: DiscoveredReplyTarget[] }>(
      "/v1/reply-targets/discover",
      { method: "POST", body: JSON.stringify(data ?? {}) },
      token,
    ),

  discoverWatchlistTargets: (token: string) =>
    request<{ source: string; message?: string; targets: DiscoveredReplyTarget[] }>(
      "/v1/reply-targets/discover/watchlist",
      { method: "POST", body: "{}" },
      token,
    ),

  discoverQuoteOpportunities: (token: string) =>
    request<{ source: string; message?: string; targets: DiscoveredReplyTarget[] }>(
      "/v1/reply-targets/discover/quotes",
      { method: "POST", body: "{}" },
      token,
    ),

  getDailyBriefing: (token: string) =>
    request<BriefingResponse>("/v1/growth/briefing", {}, token),

  runQuickReplies: (token: string) =>
    request<{ imported: number; drafted: number; message: string }>(
      "/v1/growth/quick-replies",
      { method: "POST", body: "{}" },
      token,
    ),

  fixReplyTargetFromUrl: (token: string, targetId: string, url: string) =>
    request<ReplyTarget>(
      `/v1/reply-targets/${targetId}/fix-from-url`,
      { method: "POST", body: JSON.stringify({ url }) },
      token,
    ),

  getGrowthDashboard: (token: string) =>
    request<GrowthDashboard>("/v1/growth/dashboard", {}, token),

  runLearningCycle: (token: string) =>
    request<{ applied: boolean; reason?: string; message?: string }>(
      "/v1/growth/learn",
      { method: "POST", body: "{}" },
      token,
    ),

  importReplyTargets: (token: string, targets: DiscoveredReplyTarget[]) =>
    request<{ imported: number; targets: ReplyTarget[] }>(
      "/v1/reply-targets/discover/import",
      { method: "POST", body: JSON.stringify({ targets }) },
      token,
    ),

  importReplyTargetFromUrl: (token: string, url: string) =>
    request<ReplyTarget>(
      "/v1/reply-targets/from-url/import",
      { method: "POST", body: JSON.stringify({ url }) },
      token,
    ),

  deleteReplyTarget: (token: string, targetId: string) =>
    request<void>(`/v1/reply-targets/${targetId}`, { method: "DELETE" }, token),

  generateReplyDraft: (token: string, replyTargetId: string) =>
    request<Draft>(
      "/v1/drafts/generate",
      { method: "POST", body: JSON.stringify({ reply_target_id: replyTargetId }) },
      token,
    ),
};

export { ApiError };



