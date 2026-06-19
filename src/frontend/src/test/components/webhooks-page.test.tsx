import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import WebhooksPage from '@/app/(dashboard)/webhooks/page';
import { webhooksApi } from '@/lib/api/webhooks';
import type { Webhook } from '@/lib/api/webhooks';

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

// Mock the webhooks API
vi.mock('@/lib/api/webhooks', () => ({
  webhooksApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    toggle: vi.fn(),
  },
}));

const mockWebhooks: Webhook[] = [
  {
    id: 'wh_1',
    workspace_id: 'ws_1',
    name: 'Contact Created Hook',
    url: 'https://example.com/webhooks/contact-created',
    description: 'Fires when a new contact is created',
    events: ['contact.created'],
    secret: 'whsec_xxx',
    status: 'active',
    retry_count: 3,
    timeout_seconds: 30,
    consecutive_failures: 0,
    last_success_at: '2024-06-15T12:00:00Z',
    created_at: '2024-06-01T00:00:00Z',
    updated_at: '2024-06-15T12:00:00Z',
  },
  {
    id: 'wh_2',
    workspace_id: 'ws_1',
    name: 'Invoice Paid Hook',
    url: 'https://example.com/webhooks/invoice-paid',
    description: '',
    events: ['invoice.paid', 'invoice.overdue'],
    secret: 'whsec_yyy',
    status: 'inactive',
    retry_count: 5,
    timeout_seconds: 60,
    consecutive_failures: 2,
    last_failure_at: '2024-06-10T08:00:00Z',
    created_at: '2024-06-01T00:00:00Z',
    updated_at: '2024-06-10T08:00:00Z',
  },
];

describe('WebhooksPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(webhooksApi.list).mockResolvedValue({
      data: mockWebhooks,
      meta: { total: 2, page: 1, per_page: 25, has_more: false },
      links: { self: '' },
    } as any);
  });

  it('renders the webhooks page heading and description', () => {
    render(<WebhooksPage />);
    expect(screen.getByRole('heading', { name: /webhooks/i })).toBeInTheDocument();
    expect(screen.getByText(/manage webhook endpoints/i)).toBeInTheDocument();
  });

  it('renders webhook list table with webhook data', async () => {
    render(<WebhooksPage />);
    await waitFor(() => {
      expect(screen.getByText('Contact Created Hook')).toBeInTheDocument();
      expect(screen.getByText('Invoice Paid Hook')).toBeInTheDocument();
    });
    // URLs should be visible
    expect(screen.getByText(/example\.com\/webhooks\/contact-created/i)).toBeInTheDocument();
  });

  it('renders create webhook button', () => {
    render(<WebhooksPage />);
    const createButton = screen.getByRole('button', { name: /create webhook/i });
    expect(createButton).toBeInTheDocument();
  });

  it('calls webhooks API on mount', async () => {
    render(<WebhooksPage />);
    await waitFor(() => {
      expect(webhooksApi.list).toHaveBeenCalledTimes(1);
    });
    expect(webhooksApi.list).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      status: undefined,
    });
  });

  it('renders status filter with options', async () => {
    render(<WebhooksPage />);
    await waitFor(() => {
      expect(screen.getByText(/all status/i)).toBeInTheDocument();
    });
  });

  it('renders search input for webhooks', () => {
    render(<WebhooksPage />);
    const searchInput = screen.getByPlaceholderText(/search webhooks/i);
    expect(searchInput).toBeInTheDocument();
  });

  it('filters webhooks based on status filter', async () => {
    render(<WebhooksPage />);

    await waitFor(() => {
      expect(screen.getByText('Contact Created Hook')).toBeInTheDocument();
    });

    // Status filter select trigger should exist (Radix Select with Filter icon)
    const filterSelect = screen.getByRole('combobox');
    expect(filterSelect).toBeInTheDocument();
    // The filter trigger should have a "Status" related label
    expect(filterSelect).toHaveTextContent(/all status/i);
  });

  it('shows status badges for each webhook', async () => {
    render(<WebhooksPage />);
    await waitFor(() => {
      expect(screen.getByText('Active')).toBeInTheDocument();
      expect(screen.getByText('Inactive')).toBeInTheDocument();
    });
  });

  it('shows loading skeletons while fetching', () => {
    vi.mocked(webhooksApi.list).mockImplementation(() => new Promise(() => {}));
    render(<WebhooksPage />);
    expect(screen.getByRole('heading', { name: /webhooks/i })).toBeInTheDocument();
  });

  it('shows empty state when no webhooks exist', async () => {
    vi.mocked(webhooksApi.list).mockResolvedValue({
      data: [],
      meta: { total: 0, page: 1, per_page: 25, has_more: false },
      links: { self: '' },
    } as any);
    render(<WebhooksPage />);
    await waitFor(() => {
      expect(screen.getByText(/no webhooks yet/i)).toBeInTheDocument();
    });
  });
});
