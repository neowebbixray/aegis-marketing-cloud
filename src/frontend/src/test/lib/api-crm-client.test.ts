// Mock the apiClient module before importing any modules that use it
vi.mock('@/lib/api', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@/lib/api')>();
  return {
    ...mod,
    apiClient: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    },
  };
});

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { contactsApi, dealsApi, pipelinesApi, activitiesApi, customFieldsApi } from '@/lib/api/api';
import { apiClient } from '@/lib/api';

// ─── Fixtures ──────────────────────────────────────────────
const mockContact = {
  id: 'contact-1',
  workspace_id: 'ws-1',
  first_name: 'John',
  last_name: 'Doe',
  email: 'john@example.com',
  phone: '+123****7890',
  job_title: 'CEO',
  company: 'Acme Inc',
  score: 85,
  source: 'manual',
  tags: ['vip', 'enterprise'],
  custom_fields: { industry: 'tech' },
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
  deleted_at: null,
};

const mockDeal = {
  id: 'deal-1',
  workspace_id: 'ws-1',
  name: 'Big Deal',
  value: 50000,
  currency: 'USD',
  probability: 75,
  pipeline_id: 'pipe-1',
  pipeline_stage_id: 'stage-2',
  contact_id: 'contact-1',
  owner_id: 'user-1',
  status: 'open' as const,
  won_reason: null,
  lost_reason: null,
  expected_close_date: '2026-03-01',
  notes: 'Moving fast',
  tags: ['hot'],
  is_active: true,
  created_at: '2026-01-10T00:00:00Z',
  updated_at: '2026-01-20T00:00:00Z',
  deleted_at: null,
};

const mockPipeline = {
  id: 'pipe-1',
  workspace_id: 'ws-1',
  name: 'Sales Pipeline',
  description: 'Main sales process',
  stages: [
    { id: 'stage-1', name: 'Lead', order: 0, color: '#6b7280', probability: 10 },
    { id: 'stage-2', name: 'Qualified', order: 1, color: '#3b82f6', probability: 30 },
    { id: 'stage-3', name: 'Proposal', order: 2, color: '#f59e0b', probability: 60 },
    { id: 'stage-4', name: 'Closed Won', order: 3, color: '#10b981', probability: 100 },
  ],
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockActivity = {
  id: 'act-1',
  workspace_id: 'ws-1',
  type: 'note',
  subject: 'Initial call',
  description: 'Had a great conversation',
  contact_id: 'contact-1',
  deal_id: null,
  user_id: 'user-1',
  created_at: '2026-01-12T00:00:00Z',
  updated_at: '2026-01-12T00:00:00Z',
};

const mockCustomField = {
  id: 'cf-1',
  workspace_id: 'ws-1',
  name: 'Industry',
  key: 'industry',
  description: 'Company industry',
  field_type: 'dropdown' as const,
  config: { options: ['tech', 'finance', 'healthcare'] },
  is_required: false,
  is_active: true,
  display_order: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

// ─── Contacts API ──────────────────────────────────────────
describe('contactsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('list() calls GET /api/v1/crm/contacts with params', async () => {
    const mockResponse = { items: [mockContact], total: 1, page: 1, page_size: 20 };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse);

    const result = await contactsApi.list({ page: 1, limit: 20, search: 'john' });

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/crm/contacts', { page: 1, limit: 20, search: 'john' });
    expect(result.data).toEqual([mockContact]);
    expect(result.meta?.total).toBe(1);
  });

  it('get() calls GET /api/v1/crm/contacts/:id', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockContact);

    const result = await contactsApi.get('contact-1');

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/crm/contacts/contact-1');
    expect(result.data).toEqual(mockContact);
  });

  it('getActivities() calls GET /api/v1/crm/contacts/:id/activities', async () => {
    const mockResponse = { items: [mockActivity], total: 1, page: 1, page_size: 20 };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse);

    const result = await contactsApi.getActivities('contact-1');

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/crm/contacts/contact-1/activities');
    expect(result.data).toEqual([mockActivity]);
  });

  it('create() calls POST /api/v1/crm/contacts', async () => {
    const newContact = {
      workspace_id: 'ws-1',
      first_name: 'Jane',
      last_name: 'Smith',
      email: 'jane@example.com',
    };
    vi.mocked(apiClient.post).mockResolvedValueOnce({ ...mockContact, id: 'contact-2', ...newContact });

    const result = await contactsApi.create(newContact);

    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/crm/contacts', newContact);
    expect(result.data.first_name).toBe('Jane');
  });

  it('update() calls PATCH /api/v1/crm/contacts/:id', async () => {
    const updates = { first_name: 'Jonathan' };
    vi.mocked(apiClient.patch).mockResolvedValueOnce({ ...mockContact, ...updates });

    const result = await contactsApi.update('contact-1', updates);

    expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/crm/contacts/contact-1', updates);
    expect(result.data.first_name).toBe('Jonathan');
  });

  it('delete() calls DELETE /api/v1/crm/contacts/:id', async () => {
    vi.mocked(apiClient.delete).mockResolvedValueOnce(undefined);

    await contactsApi.delete('contact-1');

    expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/crm/contacts/contact-1');
  });

  it('search() calls GET /api/v1/crm/contacts/search', async () => {
    const mockResponse = { items: [mockContact], total: 1, page: 1, page_size: 10 };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse);

    const result = await contactsApi.search('john', { limit: 10 });

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/crm/contacts/search', { q: 'john', limit: 10 });
    expect(result.data).toEqual([mockContact]);
  });

  it('updateLeadScore() calls POST /api/v1/crm/contacts/:id/lead-score', async () => {
    const updatedContact = { ...mockContact, score: 95 };
    vi.mocked(apiClient.post).mockResolvedValueOnce(updatedContact);

    const result = await contactsApi.updateLeadScore('contact-1', 95, 'manual', { factor1: 0.5 });

    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/crm/contacts/contact-1/lead-score', {
      score: 95,
      score_source: 'manual',
      scoring_factors: { factor1: 0.5 },
    });
    expect(result.data.score).toBe(95);
  });
});

// ─── Deals API ─────────────────────────────────────────────
describe('dealsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('list() calls GET /api/v1/crm/deals with pipeline_id filter', async () => {
    const mockResponse = { items: [mockDeal], total: 1, page: 1, page_size: 100 };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse);

    const result = await dealsApi.list({ pipeline_id: 'pipe-1', limit: 100 });

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/crm/deals', { pipeline_id: 'pipe-1', limit: 100 });
    expect(result.data).toEqual([mockDeal]);
  });

  it('get() calls GET /api/v1/crm/deals/:id', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockDeal);

    const result = await dealsApi.get('deal-1');

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/crm/deals/deal-1');
    expect(result.data).toEqual(mockDeal);
  });

  it('create() calls POST /api/v1/crm/deals', async () => {
    const newDeal = { workspace_id: 'ws-1', name: 'New Deal', value: 10000, pipeline_id: 'pipe-1', pipeline_stage_id: 'stage-1', contact_id: 'contact-1' };
    vi.mocked(apiClient.post).mockResolvedValueOnce({ ...mockDeal, ...newDeal });

    const result = await dealsApi.create(newDeal);

    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/crm/deals', newDeal);
    expect(result.data.name).toBe('New Deal');
  });

  it('update() calls PATCH /api/v1/crm/deals/:id', async () => {
    const updates = { value: 75000 };
    vi.mocked(apiClient.patch).mockResolvedValueOnce({ ...mockDeal, ...updates });

    const result = await dealsApi.update('deal-1', updates);

    expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/crm/deals/deal-1', updates);
    expect(result.data.value).toBe(75000);
  });

  it('delete() calls DELETE /api/v1/crm/deals/:id', async () => {
    vi.mocked(apiClient.delete).mockResolvedValueOnce(undefined);

    await dealsApi.delete('deal-1');

    expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/crm/deals/deal-1');
  });

  it('moveStage() calls PATCH /api/v1/crm/deals/:id/stage', async () => {
    const movedDeal = { ...mockDeal, pipeline_stage_id: 'stage-3', probability: 60 };
    vi.mocked(apiClient.patch).mockResolvedValueOnce(movedDeal);

    const result = await dealsApi.moveStage('deal-1', 'stage-3');

    expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/crm/deals/deal-1/stage', { pipeline_stage_id: 'stage-3' });
    expect(result.data.pipeline_stage_id).toBe('stage-3');
  });

  it('markWon() calls PATCH /api/v1/crm/deals/:id with won_reason', async () => {
    const wonDeal = { ...mockDeal, won_reason: 'Customer signed' };
    vi.mocked(apiClient.patch).mockResolvedValueOnce(wonDeal);

    const result = await dealsApi.markWon('deal-1', 'Customer signed');

    expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/crm/deals/deal-1', { won_reason: 'Customer signed' });
    expect(result.data.won_reason).toBe('Customer signed');
  });

  it('markLost() calls PATCH /api/v1/crm/deals/:id with lost_reason', async () => {
    const lostDeal = { ...mockDeal, lost_reason: 'Budget constraints' };
    vi.mocked(apiClient.patch).mockResolvedValueOnce(lostDeal);

    const result = await dealsApi.markLost('deal-1', 'Budget constraints');

    expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/crm/deals/deal-1', { lost_reason: 'Budget constraints' });
    expect(result.data.lost_reason).toBe('Budget constraints');
  });
});

// ─── Pipelines API ─────────────────────────────────────────
describe('pipelinesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('list() calls GET /api/v1/crm/pipelines', async () => {
    const mockResponse = { items: [mockPipeline], total: 1, page: 1, page_size: 50 };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse);

    const result = await pipelinesApi.list();

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/crm/pipelines');
    expect(result.data).toEqual([mockPipeline]);
  });

  it('get() calls GET /api/v1/crm/pipelines/:id', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockPipeline);

    const result = await pipelinesApi.get('pipe-1');

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/crm/pipelines/pipe-1');
    expect(result.data).toEqual(mockPipeline);
  });

  it('create() calls POST /api/v1/crm/pipelines', async () => {
    const newPipeline = {
      workspace_id: 'ws-1',
      name: 'New Pipeline',
      stages: [{ name: 'Stage 1', order: 0, color: '#000', probability: 10 }],
    };
    vi.mocked(apiClient.post).mockResolvedValueOnce({ ...mockPipeline, ...newPipeline });

    const result = await pipelinesApi.create(newPipeline as any);

    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/crm/pipelines', newPipeline);
    expect(result.data.name).toBe('New Pipeline');
  });

  it('update() calls PATCH /api/v1/crm/pipelines/:id', async () => {
    const updates = { name: 'Updated Pipeline' };
    vi.mocked(apiClient.patch).mockResolvedValueOnce({ ...mockPipeline, ...updates });

    const result = await pipelinesApi.update('pipe-1', updates);

    expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/crm/pipelines/pipe-1', updates);
    expect(result.data.name).toBe('Updated Pipeline');
  });

  it('delete() calls DELETE /api/v1/crm/pipelines/:id', async () => {
    vi.mocked(apiClient.delete).mockResolvedValueOnce(undefined);

    await pipelinesApi.delete('pipe-1');

    expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/crm/pipelines/pipe-1');
  });

  it('reorderStages() calls PUT /api/v1/crm/pipelines/:id/stages/reorder', async () => {
    const reorderedIds = ['stage-4', 'stage-3', 'stage-2', 'stage-1'];
    vi.mocked(apiClient.put).mockResolvedValueOnce(mockPipeline);

    const result = await pipelinesApi.reorderStages('pipe-1', reorderedIds);

    expect(apiClient.put).toHaveBeenCalledWith('/api/v1/crm/pipelines/pipe-1/stages/reorder', { stage_ids: reorderedIds });
    expect(result.data).toEqual(mockPipeline);
  });
});

// ─── Activities API ────────────────────────────────────────
describe('activitiesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('list() calls GET /api/v1/crm/activities', async () => {
    const mockResponse = { items: [mockActivity], total: 1, page: 1, page_size: 20 };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse);

    const result = await activitiesApi.list({ contact_id: 'contact-1', limit: 20 });

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/crm/activities', { contact_id: 'contact-1', limit: 20 });
    expect(result.data).toEqual([mockActivity]);
  });

  it('create() calls POST /api/v1/crm/activities', async () => {
    const newActivity = { workspace_id: 'ws-1', type: 'note' as const, subject: 'Follow-up', contact_id: 'contact-1' };
    vi.mocked(apiClient.post).mockResolvedValueOnce({ ...mockActivity, ...newActivity });

    const result = await activitiesApi.create(newActivity);

    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/crm/activities', newActivity);
    expect(result.data.subject).toBe('Follow-up');
  });
});

// ─── Custom Fields API ─────────────────────────────────────
describe('customFieldsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('list() calls GET /api/v1/custom-fields', async () => {
    const mockResponse = { items: [mockCustomField], total: 1, page: 1, page_size: 50 };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse);

    const result = await customFieldsApi.list({ is_active: true });

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/custom-fields', { is_active: true });
    expect(result.data).toEqual([mockCustomField]);
  });

  it('get() calls GET /api/v1/custom-fields/:id', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockCustomField);

    const result = await customFieldsApi.get('cf-1');

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/custom-fields/cf-1');
    expect(result.data).toEqual(mockCustomField);
  });

  it('create() calls POST /api/v1/custom-fields', async () => {
    const newField = { workspace_id: 'ws-1', name: 'New Field', key: 'new_field', field_type: 'text' as const };
    vi.mocked(apiClient.post).mockResolvedValueOnce({ ...mockCustomField, ...newField });

    const result = await customFieldsApi.create(newField);

    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/custom-fields', newField);
    expect(result.data.name).toBe('New Field');
  });

  it('update() calls PATCH /api/v1/custom-fields/:id', async () => {
    const updates = { name: 'Updated Field' };
    vi.mocked(apiClient.patch).mockResolvedValueOnce({ ...mockCustomField, ...updates });

    const result = await customFieldsApi.update('cf-1', updates);

    expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/custom-fields/cf-1', updates);
    expect(result.data.name).toBe('Updated Field');
  });

  it('delete() calls DELETE /api/v1/custom-fields/:id', async () => {
    vi.mocked(apiClient.delete).mockResolvedValueOnce(undefined);

    await customFieldsApi.delete('cf-1');

    expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/custom-fields/cf-1');
  });

  it('reorder() calls PUT /api/v1/custom-fields/reorder', async () => {
    vi.mocked(apiClient.put).mockResolvedValueOnce(undefined);

    await customFieldsApi.reorder(['cf-1', 'cf-2', 'cf-3']);

    expect(apiClient.put).toHaveBeenCalledWith('/api/v1/custom-fields/reorder', { field_ids: ['cf-1', 'cf-2', 'cf-3'] });
  });
});

// ─── Error Handling ────────────────────────────────────────
describe('CRM API error propagation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('handles 404 from contactsApi.get', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Not Found'));

    await expect(contactsApi.get('nonexistent')).rejects.toThrow('Not Found');
  });

  it('handles 404 from dealsApi.get', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Not Found'));

    await expect(dealsApi.get('nonexistent')).rejects.toThrow('Not Found');
  });

  it('handles validation errors from contactsApi.create', async () => {
    vi.mocked(apiClient.post).mockRejectedValueOnce(new Error('Validation failed'));

    await expect(contactsApi.create({ workspace_id: '' } as any)).rejects.toThrow('Validation failed');
  });

  it('handles validation errors from dealsApi.moveStage', async () => {
    vi.mocked(apiClient.patch).mockRejectedValueOnce(new Error('Invalid stage transition'));

    await expect(dealsApi.moveStage('deal-1', 'invalid-stage')).rejects.toThrow('Invalid stage transition');
  });

  it('handles network failures on pipelinesApi.list', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new TypeError('Failed to fetch'));

    await expect(pipelinesApi.list()).rejects.toThrow('Failed to fetch');
  });
});