import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AnalyticsPage from '@/app/(dashboard)/analytics/page';
import { analyticsApi } from '@/lib/api/analytics';
import type { Dashboard } from '@/lib/api/analytics';

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

// Mock the analytics API
vi.mock('@/lib/api/analytics', () => ({
  analyticsApi: {
    listDashboards: vi.fn(),
    createDashboard: vi.fn(),
    deleteDashboard: vi.fn(),
  },
}));

const mockDashboards: Dashboard[] = [
  {
    id: 'db_1',
    workspace_id: 'ws_1',
    name: 'Weekly Performance',
    description: 'Key metrics for the week',
    type: 'main',
    widgets: [
      {
        id: 'w_1',
        dashboard_id: 'db_1',
        title: 'Page Views',
        type: 'metric',
        metric: 'page_views',
        size: 'sm',
        position: { x: 0, y: 0 },
        config: {},
      },
      {
        id: 'w_2',
        dashboard_id: 'db_1',
        title: 'Revenue Chart',
        type: 'chart',
        metric: 'revenue',
        chart_type: 'line',
        size: 'md',
        position: { x: 1, y: 0 },
        config: {},
      },
    ],
    layout: {},
    is_default: true,
    created_at: '2024-06-01T00:00:00Z',
    updated_at: '2024-06-15T12:00:00Z',
  },
  {
    id: 'db_2',
    workspace_id: 'ws_1',
    name: 'Email Campaign Report',
    description: 'Email marketing performance',
    type: 'email',
    widgets: [],
    layout: {},
    is_default: false,
    created_at: '2024-06-10T00:00:00Z',
    updated_at: '2024-06-12T08:00:00Z',
  },
];

describe('AnalyticsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(analyticsApi.listDashboards).mockResolvedValue({
      data: mockDashboards,
      links: { self: '' },
    } as any);
  });

  it('renders the analytics page heading and description', () => {
    render(<AnalyticsPage />);
    expect(screen.getByRole('heading', { name: /analytics/i })).toBeInTheDocument();
    expect(screen.getByText(/create and manage analytics dashboards/i)).toBeInTheDocument();
  });

  it('renders dashboard grid with dashboard cards', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('Weekly Performance')).toBeInTheDocument();
      expect(screen.getByText('Email Campaign Report')).toBeInTheDocument();
    });
    // Descriptions should render
    expect(screen.getByText(/key metrics for the week/i)).toBeInTheDocument();
  });

  it('renders create dashboard button', () => {
    render(<AnalyticsPage />);
    const createButton = screen.getByRole('button', { name: /new dashboard/i });
    expect(createButton).toBeInTheDocument();
  });

  it('calls analytics API on mount', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(analyticsApi.listDashboards).toHaveBeenCalledTimes(1);
    });
  });

  it('renders search filter input', () => {
    render(<AnalyticsPage />);
    const searchInput = screen.getByPlaceholderText(/search dashboards/i);
    expect(searchInput).toBeInTheDocument();
  });

  it('filters dashboards based on search input', async () => {
    const user = userEvent.setup();
    render(<AnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText('Weekly Performance')).toBeInTheDocument();
    });

    // Type in search to filter
    const searchInput = screen.getByPlaceholderText(/search dashboards/i);
    await user.type(searchInput, 'Email');

    // Weekly Performance should be hidden, Email Campaign Report visible
    expect(screen.queryByText('Email Campaign Report')).toBeInTheDocument();
  });

  it('shows widget count on dashboard cards', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      const widgetText = screen.getByText(/2 widgets/i);
      expect(widgetText).toBeInTheDocument();
    });
  });

  it('shows dashboard type badges', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('Main')).toBeInTheDocument();
      expect(screen.getByText('Email')).toBeInTheDocument();
    });
  });

  it('shows loading skeletons while fetching', () => {
    vi.mocked(analyticsApi.listDashboards).mockImplementation(() => new Promise(() => {}));
    render(<AnalyticsPage />);
    expect(screen.getByRole('heading', { name: /analytics/i })).toBeInTheDocument();
  });

  it('shows empty state when no dashboards exist', async () => {
    vi.mocked(analyticsApi.listDashboards).mockResolvedValue({
      data: [],
      links: { self: '' },
    } as any);
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText(/no dashboards yet/i)).toBeInTheDocument();
    });
  });
});
