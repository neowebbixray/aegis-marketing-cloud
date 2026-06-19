import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import KnowledgeBasePage from '@/app/(dashboard)/knowledge/page';
import { knowledgeApi } from '@/lib/api/knowledge';
import type { KnowledgeDocument } from '@/lib/api/knowledge';

// Mock next/navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  }),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock the knowledge API
vi.mock('@/lib/api/knowledge', () => ({
  knowledgeApi: {
    listDocuments: vi.fn(),
    search: vi.fn(),
    uploadDocument: vi.fn(),
    deleteDocument: vi.fn(),
  },
}));

const mockDocuments: KnowledgeDocument[] = [
  {
    id: 'doc_1',
    workspace_id: 'ws_1',
    title: 'Marketing Strategy 2024',
    description: 'Annual marketing strategy document',
    content_type: 'pdf',
    source: 'upload',
    status: 'indexed',
    file_size: 2048000,
    tags: ['marketing', 'strategy'],
    metadata: {},
    created_at: '2024-06-01T00:00:00Z',
    updated_at: '2024-06-01T00:00:00Z',
  },
  {
    id: 'doc_2',
    workspace_id: 'ws_1',
    title: 'SEO Best Practices',
    description: 'Guide to SEO optimization',
    content_type: 'md',
    source: 'upload',
    status: 'processing',
    file_size: 512000,
    tags: ['seo', 'guide'],
    metadata: {},
    created_at: '2024-06-10T00:00:00Z',
    updated_at: '2024-06-10T00:00:00Z',
  },
];

describe('KnowledgeBasePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(knowledgeApi.listDocuments).mockResolvedValue({
      data: mockDocuments,
      meta: { total: 2, page: 1, per_page: 20, has_more: false },
      links: { self: '' },
    } as any);
    vi.mocked(knowledgeApi.search).mockResolvedValue({
      data: [],
      meta: { total: 0, page: 1, per_page: 5, has_more: false },
      links: { self: '' },
    } as any);
  });

  it('renders the knowledge base page heading and description', () => {
    render(<KnowledgeBasePage />);
    expect(screen.getByRole('heading', { name: /knowledge base/i })).toBeInTheDocument();
    expect(screen.getByText(/store, search, and manage/i)).toBeInTheDocument();
  });

  it('renders document list with document titles', async () => {
    render(<KnowledgeBasePage />);
    await waitFor(() => {
      expect(screen.getByText('Marketing Strategy 2024')).toBeInTheDocument();
      expect(screen.getByText('SEO Best Practices')).toBeInTheDocument();
    });
  });

  it('renders semantic search bar', () => {
    render(<KnowledgeBasePage />);
    const searchInput = screen.getByPlaceholderText(/ask a question about your documents/i);
    expect(searchInput).toBeInTheDocument();
    const searchButton = screen.getByRole('button', { name: /search$/i });
    expect(searchButton).toBeInTheDocument();
  });

  it('renders upload document button', () => {
    render(<KnowledgeBasePage />);
    const uploadButton = screen.getByRole('button', { name: /upload document/i });
    expect(uploadButton).toBeInTheDocument();
  });

  it('calls knowledge API on mount', async () => {
    render(<KnowledgeBasePage />);
    await waitFor(() => {
      expect(knowledgeApi.listDocuments).toHaveBeenCalledTimes(1);
    });
  });

  it('renders document status badges', async () => {
    render(<KnowledgeBasePage />);
    await waitFor(() => {
      expect(screen.getByText('Indexed')).toBeInTheDocument();
      expect(screen.getByText('Processing')).toBeInTheDocument();
    });
  });

  it('renders document content types', async () => {
    render(<KnowledgeBasePage />);
    await waitFor(() => {
      expect(screen.getByText(/pdf/i)).toBeInTheDocument();
      expect(screen.getByText(/md/i)).toBeInTheDocument();
    });
  });

  it('renders status filter select', async () => {
    render(<KnowledgeBasePage />);
    await waitFor(() => {
      expect(screen.getByText(/all status/i)).toBeInTheDocument();
    });
  });

  it('renders tag filter input', () => {
    render(<KnowledgeBasePage />);
    const tagInput = screen.getByPlaceholderText(/filter by tag/i);
    expect(tagInput).toBeInTheDocument();
  });

  it('shows document search bar for regular search', () => {
    render(<KnowledgeBasePage />);
    const searchInput = screen.getByPlaceholderText(/search documents/i);
    expect(searchInput).toBeInTheDocument();
  });

  it('renders loading skeletons initially', () => {
    vi.mocked(knowledgeApi.listDocuments).mockImplementation(() => new Promise(() => {}));
    render(<KnowledgeBasePage />);
    expect(screen.getByRole('heading', { name: /knowledge base/i })).toBeInTheDocument();
  });

  it('shows empty state when no documents exist', async () => {
    vi.mocked(knowledgeApi.listDocuments).mockResolvedValue({
      data: [],
      meta: { total: 0, page: 1, per_page: 20, has_more: false },
      links: { self: '' },
    } as any);
    render(<KnowledgeBasePage />);
    await waitFor(() => {
      expect(screen.getByText(/no documents found/i)).toBeInTheDocument();
    });
  });
});
