// ─── AI API ───────────────────────────────────────────────
// Backend routes: /api/v1/ai/...

import { apiClient } from '@/lib/api';
import type { ApiResponse, PaginatedResponse } from '@/types';

// ─── Types ─────────────────────────────────────────────────

export type AgentStatus = 'idle' | 'running' | 'error' | 'paused';
export type AgentCapability = 'lead-scoring' | 'content-generation' | 'sentiment-analysis' | 'classification' | 'recommendation' | 'chat' | 'summarization' | 'translation' | 'image_analysis' | 'email_composer' | 'intent-detection' | 'ab-testing' | 'segment-analysis' | 'forecasting';
export type ConversationStatus = 'active' | 'archived' | 'completed' | 'resolved';
export type ContentType = 'email' | 'social' | 'ad' | 'landing-page' | 'push' | 'sms' | 'blog_post' | 'social_post' | 'landing_page' | 'ad_copy' | 'product_description' | 'newsletter' | 'press_release';
export type ClassificationTask = 'intent' | 'sentiment' | 'topic' | 'priority' | 'stage';

export interface Agent {
  id: string;
  tenant_id: string;
  workspace_id?: string;
  name: string;
  description: string;
  capabilities: AgentCapability[];
  status: AgentStatus;
  model: string;
  temperature?: number;
  max_tokens?: number;
  is_active: boolean;
  last_run_at?: string | null;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CreateAgentRequest {
  name: string;
  description?: string;
  capabilities: AgentCapability[];
  model?: string;
  temperature?: number;
  max_tokens?: number;
  config?: Record<string, unknown>;
}

export interface UpdateAgentRequest {
  name?: string;
  description?: string;
  capabilities?: AgentCapability[];
  status?: AgentStatus;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  config?: Record<string, unknown>;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tokens_used?: number;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface Conversation {
  id: string;
  tenant_id: string;
  agent_id: string;
  title: string;
  status: ConversationStatus;
  messages: Message[];
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CreateConversationRequest {
  agent_id: string;
  title: string;
  initial_message?: string;
}

export interface SendMessageRequest {
  content: string;
  metadata?: Record<string, unknown>;
}

export interface GenerationRequest {
  agent_id?: string;
  content_type: ContentType;
  prompt: string;
  context?: Record<string, unknown>;
  tone?: string;
  audience?: string;
  length?: 'short' | 'medium' | 'long';
  target_audience?: string;
  keywords?: string[];
}

export interface GenerationResult {
  id: string;
  content: string;
  content_type: ContentType;
  tokens_used: number;
  model: string;
  latency_ms: number;
  processing_time_ms: number;
  created_at: string;
}

export interface ClassificationRequest {
  text: string;
  task: ClassificationTask;
  categories?: string[];
}

export interface ClassificationResult {
  text: string;
  task: ClassificationTask;
  label: string;
  confidence: number;
  categories?: Record<string, number>;
  explanation?: string;
}

export interface LeadScoreRequest {
  contact_id: string;
  tenant_id: string;
}

export interface LeadScoreResponse {
  contact_id: string;
  score: number;
  confidence: number;
  factors: Record<string, number>;
}

// ─── API ───────────────────────────────────────────────────

export const aiApi = {
  // Agents
  listAgents: (params?: Record<string, string | number | boolean | undefined>) =>
    apiClient.get<PaginatedResponse<Agent>>('/api/v1/ai/agents', params),

  getAgent: (id: string) =>
    apiClient.get<ApiResponse<Agent>>(`/api/v1/ai/agents/${id}`),

  createAgent: (data: CreateAgentRequest) =>
    apiClient.post<ApiResponse<Agent>>('/api/v1/ai/agents', data),

  updateAgent: (id: string, data: UpdateAgentRequest) =>
    apiClient.patch<ApiResponse<Agent>>(`/api/v1/ai/agents/${id}`, data),

  deleteAgent: (id: string) =>
    apiClient.delete(`/api/v1/ai/agents/${id}`),

  // Conversations
  listConversations: (agentId: string, params?: Record<string, string | number | boolean | undefined>) =>
    apiClient.get<PaginatedResponse<Conversation>>(`/api/v1/ai/agents/${agentId}/conversations`, params),

  getConversation: (id: string) =>
    apiClient.get<ApiResponse<Conversation>>(`/api/v1/ai/conversations/${id}`),

  createConversation: (data: CreateConversationRequest) =>
    apiClient.post<ApiResponse<Conversation>>('/api/v1/ai/conversations', data),

  sendMessage: (conversationId: string, data: SendMessageRequest) =>
    apiClient.post<ApiResponse<Message>>(`/api/v1/ai/conversations/${conversationId}/messages`, data),

  deleteConversation: (id: string) =>
    apiClient.delete<ApiResponse<void>>(`/api/v1/ai/conversations/${id}`),

  // Content Generation
  listGenerations: (params?: Record<string, string | number | boolean | undefined>) =>
    apiClient.get<PaginatedResponse<GenerationResult>>('/api/v1/ai/generations', params),

  generate: (data: GenerationRequest) =>
    apiClient.post<ApiResponse<GenerationResult>>('/api/v1/ai/generate', data),

  // Alias for ContentGenerationPage
  generateContent: (data: GenerationRequest) =>
    apiClient.post<ApiResponse<GenerationResult>>('/api/v1/ai/generate', data),

  // Classification
  classify: (data: ClassificationRequest) =>
    apiClient.post<ApiResponse<ClassificationResult>>('/api/v1/ai/classify', data),

  // Lead Scoring
  scoreLead: (data: LeadScoreRequest) =>
    apiClient.post<ApiResponse<LeadScoreResponse>>('/api/v1/ai/lead-score', data),

  // Agent Execution
  runAgent: (id: string, data: { input: string }) =>
    apiClient.post<ApiResponse<GenerationResult>>(`/api/v1/ai/agents/${id}/run`, data),
};
