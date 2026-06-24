import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AiSuitePage from '@/app/(dashboard)/ai-suite/page';
import { aiApi } from '@/lib/api/ai';
import type { Agent } from '@/lib/api/ai';

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

// Mock the AI API
vi.mock('@/lib/api/ai', () => ({
  aiApi: {
    listAgents: vi.fn(),
    createAgent: vi.fn(),
  },
}));

const mockAgents: Agent[] = [
  {
    id: 'agent_1',
    tenant_id: 'tenant_1',
    workspace_id: 'ws_1',
    name: 'Content Specialist',
    description: 'Generates marketing content',
    capabilities: ['content-generation', 'email_composer'] as Agent['capabilities'],
    status: 'idle',
    config: {},
    model: 'gpt-4',
    temperature: 0.7,
    max_tokens: 2048,
    is_active: true,
    last_run_at: '2024-06-15T10:00:00Z',
    created_at: '2024-06-01T00:00:00Z',
    updated_at: '2024-06-15T10:00:00Z',
  },
  {
    id: 'agent_2',
    tenant_id: 'tenant_1',
    workspace_id: 'ws_1',
    name: 'Sentiment Analyzer',
    description: 'Analyzes customer sentiment',
    capabilities: ['sentiment-analysis', 'classification'] as Agent['capabilities'],
    status: 'running',
    config: {},
    model: 'gpt-4-turbo',
    temperature: 0.3,
    max_tokens: 1024,
    is_active: true,
    created_at: '2024-06-05T00:00:00Z',
    updated_at: '2024-06-16T08:00:00Z',
  },
];

describe('AiSuitePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(aiApi.listAgents).mockResolvedValue({
      data: mockAgents,
      links: { self: '' },
    } as any);
  });

  it('renders the AI suite page heading and description', () => {
    render(<AiSuitePage />);
    expect(screen.getByRole('heading', { name: /ai suite/i })).toBeInTheDocument();
    expect(screen.getByText(/ai-powered marketing agents/i)).toBeInTheDocument();
  });

  it('renders agent cards with agent names', async () => {
    render(<AiSuitePage />);
    await waitFor(() => {
      expect(screen.getByText('Content Specialist')).toBeInTheDocument();
      expect(screen.getByText('Sentiment Analyzer')).toBeInTheDocument();
    });
  });

  it('renders capability badges on agent cards', async () => {
    render(<AiSuitePage />);
    await waitFor(() => {
      // Content Gen (from content_generation) and Email Composer (from email_composer)
      expect(screen.getByText('Content Gen')).toBeInTheDocument();
      expect(screen.getByText('Email Composer')).toBeInTheDocument();
    });
    // Sentiment Analyzer capabilities
    expect(screen.getByText('Sentiment')).toBeInTheDocument();
    expect(screen.getByText('Classification')).toBeInTheDocument();
  });

  it('renders create agent button', () => {
    render(<AiSuitePage />);
    const createButton = screen.getByRole('button', { name: /create agent/i });
    expect(createButton).toBeInTheDocument();
  });

  it('calls AI API on mount', async () => {
    render(<AiSuitePage />);
    await waitFor(() => {
      expect(aiApi.listAgents).toHaveBeenCalledTimes(1);
    });
  });

  it('renders agent type/status filter', async () => {
    render(<AiSuitePage />);
    await waitFor(() => {
      expect(screen.getByText(/all status/i)).toBeInTheDocument();
    });
  });

  it('renders capability filter', async () => {
    render(<AiSuitePage />);
    await waitFor(() => {
      expect(screen.getByText(/all capabilities/i)).toBeInTheDocument();
    });
  });

  it('shows stats cards with agent count', async () => {
    render(<AiSuitePage />);
    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument(); // Total agents
      expect(screen.getByText(/1 currently running/i)).toBeInTheDocument();
    });
  });

  it('renders status badges for each agent', async () => {
    render(<AiSuitePage />);
    await waitFor(() => {
      expect(screen.getByText('Idle')).toBeInTheDocument();
      expect(screen.getByText('Running')).toBeInTheDocument();
    });
  });

  it('renders the generate content button', () => {
    render(<AiSuitePage />);
    const generateButton = screen.getByRole('button', { name: /generate content/i });
    expect(generateButton).toBeInTheDocument();
  });

  it('shows loading skeletons while fetching agents', () => {
    vi.mocked(aiApi.listAgents).mockImplementation(() => new Promise(() => {}));
    render(<AiSuitePage />);
    expect(screen.getByRole('heading', { name: /ai suite/i })).toBeInTheDocument();
  });

  it('shows empty state when no agents exist', async () => {
    vi.mocked(aiApi.listAgents).mockResolvedValue({
      data: [],
      links: { self: '' },
    } as any);
    render(<AiSuitePage />);
    await waitFor(() => {
      expect(screen.getByText(/no agents found/i)).toBeInTheDocument();
    });
  });

  it('renders agent "Open" and chat buttons', async () => {
    render(<AiSuitePage />);
    await waitFor(() => {
      const openButtons = screen.getAllByRole('button', { name: /open/i });
      expect(openButtons.length).toBeGreaterThan(0);
    });
  });
});
