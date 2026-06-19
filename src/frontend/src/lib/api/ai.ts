// ─── AI API ────────────────────────────────────────────────
// Backend routes: /api/v1/ai/...

import { apiClient } from '@/lib/api';
import type { ApiResponse, PaginatedResponse } from '@/types';

// ─── Types ─────────────────────────────────────────────────

export type AgentStatus = 'idle' | 'running' | 'error' | 'paused';

export type AgentCapability =
  | 'content_generation'
  | 'classification'
  | 'sentiment_analysis'
  | 'lead_scoring'
  | 'email_composer'
  | 'chat'
  | 'summarization'
  | 'translation'
  | 'image_analysis'
  | 'recommendation';

export type ConversationStatus = 'active' | 'archived' | 'resolved';

export type ContentType =
  | 'blog_post'
  | 'social_post'
  | 'email'
  | 'landing_page'
  | 'ad_copy'
  | 'product_description'
  | 'newsletter'
  | 'press_release';

export type ClassificationTask =
  | 'sentiment'
  | 'intent'
  | 'topic'
  | 'spam'
  | 'category'
  | 'priority';

export interface Agent {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  capabilities: AgentCapability[];
  status: AgentStatus;
  config: Record<string, unknown>;
  model: string;
  temperature: number;
  max_tokens: number;
  system_prompt?: string;
  is_active: boolean;
  last_run_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateAgentRequest {
  name: string;
  description?: string;
  capabilities: AgentCapability[];
  config?: Record<string, unknown>;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  system_prompt?: string;
}

export interface UpdateAgentRequest {
  name?: string;
  description?: string;
  capabilities?: AgentCapability[];
  config?: Record<string, unknown>;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  system_prompt?: string;
  is_active?: boolean;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata?: Record<string, unknown>;
  tokens_used?: number;
  created_at: string;
}

export interface Conversation {
  id: string;
  workspace_id: string;
  agent_id?: string;
  title: string;
  status: ConversationStatus;
  messages: Message[];
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CreateConversationRequest {
  agent_id?: string;
  title?: string;
  metadata?: Record<string, unknown>;
}

export interface SendMessageRequest {
  content: string;
  metadata?: Record<string, unknown>;
}

export interface GenerationRequest {
  content_type: ContentType;
  prompt: string;
  tone?: string;
  length?: 'short' | 'medium' | 'long';
  keywords?: string[];
  target_audience?: string;
  brand_voice?: string;
  language?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface GenerationResult {
  id: string;
  content: string;
  content_type: ContentType;
  title?: string;
  tokens_used: number;
  model: string;
  processing_time_ms: number;
  created_at: string;
}

export interface ClassificationRequest {
  text: string;
  task: ClassificationTask;
  categories?: string[];
  multi_label?: boolean;
  threshold?: number;
}

export interface ClassificationResult {
  id: string;
  task: ClassificationTask;
  predictions: Array<{
    label: string;
    score: number;
  }>;
  processing_time_ms: number;
  model: string;
}

// ─── AI API Client ─────────────────────────────────────────

export const aiApi = {
  // ── Agents ──

  /** List AI agents */
  listAgents: (params?: { status?: AgentStatus; capability?: AgentCapability }) =>
    apiClient
      .get<Agent[]>('/api/v1/ai/agents', params as Record<string, string | number | boolean | undefined>)
      .then((items) => ({ data: items }) as unknown as ApiResponse<Agent[]>),

  /** Get agent by ID */
  getAgent: (id: string) =>
    apiClient.get<Agent>(`/api/v1/ai/agents/${id}`).then(
      (data) => ({ data }) as ApiResponse<Agent>
    ),

  /** Create a new agent */
  createAgent: (data: CreateAgentRequest) =>
    apiClient.post<Agent>('/api/v1/ai/agents', data).then(
      (data) => ({ data }) as ApiResponse<Agent>
    ),

  /** Update an agent */
  updateAgent: (id: string, data: UpdateAgentRequest) =>
    apiClient.patch<Agent>(`/api/v1/ai/agents/${id}`, data).then(
      (data) => ({ data }) as ApiResponse<Agent>
    ),

  /** Delete an agent */
  deleteAgent: (id: string) =>
    apiClient.delete<void>(`/api/v1/ai/agents/${id}`),

  /** Run an agent (trigger its capability) */
  runAgent: (id: string, input: Record<string, unknown>) =>
    apiClient.post<{ result: unknown; execution_time_ms: number }>(
      `/api/v1/ai/agents/${id}/run`, input
    ).then((data) => ({ data }) as ApiResponse<{ result: unknown; execution_time_ms: number }>),

  // ── Conversations ──

  /** List conversations */
  listConversations: (params?: {
    page?: number;
    limit?: number;
    status?: ConversationStatus;
    agent_id?: string;
  }) =>
    apiClient
      .get<{ items: Conversation[]; total: number; page: number; page_size: number }>(
        '/api/v1/ai/conversations',
        params as Record<string, string | number | boolean | undefined>
      )
      .then((res) => ({
        data: res.items,
        meta: {
          page: res.page,
          per_page: res.page_size,
          total: res.total,
          has_more: res.page * res.page_size < res.total,
        },
        links: { self: '' },
      })) as Promise<PaginatedResponse<Conversation>>,

  /** Get conversation with messages */
  getConversation: (id: string) =>
    apiClient.get<Conversation>(`/api/v1/ai/conversations/${id}`).then(
      (data) => ({ data }) as ApiResponse<Conversation>
    ),

  /** Create a new conversation */
  createConversation: (data: CreateConversationRequest) =>
    apiClient.post<Conversation>('/api/v1/ai/conversations', data).then(
      (data) => ({ data }) as ApiResponse<Conversation>
    ),

  /** Delete a conversation */
  deleteConversation: (id: string) =>
    apiClient.delete<void>(`/api/v1/ai/conversations/${id}`),

  /** Send a message and get a response (streaming-capable) */
  sendMessage: async (
    conversationId: string,
    data: SendMessageRequest,
    onStream?: (chunk: string) => void
  ): Promise<ApiResponse<Message>> => {
    if (!onStream) {
      return apiClient
        .post<Message>(`/api/v1/ai/conversations/${conversationId}/messages`, data)
        .then((msg) => ({ data: msg }) as ApiResponse<Message>);
    }

    // Streaming mode
    const token = JSON.parse(localStorage.getItem('auth-store') || '{}')?.state?.token || '';
    const response = await fetch(
      `/api/v1/ai/conversations/${conversationId}/messages/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(data),
      }
    );

    if (!response.ok || !response.body) {
      throw new Error('Streaming request failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullContent = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      fullContent += chunk;
      onStream(chunk);
    }

    return {
      data: {
        id: crypto.randomUUID(),
        conversation_id: conversationId,
        role: 'assistant',
        content: fullContent,
        created_at: new Date().toISOString(),
      },
    } as ApiResponse<Message>;
  },

  // ── Content Generation ──

  /** Generate content */
  generateContent: (request: GenerationRequest) =>
    apiClient.post<GenerationResult>('/api/v1/ai/generate', request).then(
      (data) => ({ data }) as ApiResponse<GenerationResult>
    ),

  /** Generate content in batch */
  generateContentBatch: (requests: GenerationRequest[]) =>
    apiClient.post<GenerationResult[]>('/api/v1/ai/generate/batch', { requests }).then(
      (items) => ({ data: items }) as unknown as ApiResponse<GenerationResult[]>
    ),

  /** Get generation history */
  listGenerations: (params?: { page?: number; limit?: number; content_type?: ContentType }) =>
    apiClient
      .get<{ items: GenerationResult[]; total: number; page: number; page_size: number }>(
        '/api/v1/ai/generations',
        params as Record<string, string | number | boolean | undefined>
      )
      .then((res) => ({
        data: res.items,
        meta: {
          page: res.page,
          per_page: res.page_size,
          total: res.total,
          has_more: res.page * res.page_size < res.total,
        },
        links: { self: '' },
      })) as Promise<PaginatedResponse<GenerationResult>>,

  // ── Classification ──

  /** Classify text */
  classify: (request: ClassificationRequest) =>
    apiClient.post<ClassificationResult>('/api/v1/ai/classify', request).then(
      (data) => ({ data }) as ApiResponse<ClassificationResult>
    ),

  /** Batch classification */
  classifyBatch: (requests: ClassificationRequest[]) =>
    apiClient.post<ClassificationResult[]>('/api/v1/ai/classify/batch', { requests }).then(
      (items) => ({ data: items }) as unknown as ApiResponse<ClassificationResult[]>
    ),
};
