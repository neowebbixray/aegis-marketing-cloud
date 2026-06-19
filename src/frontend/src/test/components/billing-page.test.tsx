import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import BillingPage from '@/app/(dashboard)/billing/page';
import { billingApi } from '@/lib/api/billing';
import type { Subscription, Invoice, Wallet, UsageSummary } from '@/lib/api/billing';

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

// Mock the billing API
vi.mock('@/lib/api/billing', () => ({
  billingApi: {
    getSubscription: vi.fn(),
    listInvoices: vi.fn(),
    getWallet: vi.fn(),
    getUsageSummary: vi.fn(),
    cancelSubscription: vi.fn(),
    reactivateSubscription: vi.fn(),
    addWalletCredit: vi.fn(),
    downloadInvoice: vi.fn(),
  },
}));

const mockSubscription: Subscription = {
  id: 'sub_1',
  tenant_id: 'tenant_1',
  plan_id: 'plan_1',
  plan: {
    id: 'plan_1',
    name: 'Pro',
    slug: 'pro',
    description: 'Professional plan',
    price_monthly: 2900,
    price_yearly: 29000,
    currency: 'usd',
    features: ['Unlimited contacts', 'Email campaigns', 'Advanced analytics'],
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
  },
  status: 'active',
  current_period_start: '2024-06-01T00:00:00Z',
  current_period_end: '2024-07-01T00:00:00Z',
  cancel_at_period_end: false,
  billing_anchor: 'current_period',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-06-01T00:00:00Z',
};

const mockInvoices: Invoice[] = [
  {
    id: 'inv_1',
    tenant_id: 'tenant_1',
    subscription_id: 'sub_1',
    number: 'INV-001',
    amount_due: 2900,
    amount_paid: 2900,
    amount_remaining: 0,
    currency: 'usd',
    status: 'paid',
    billing_reason: 'subscription_create',
    due_date: '2024-06-15T00:00:00Z',
    created_at: '2024-06-01T00:00:00Z',
    lines: [],
  },
];

const mockWallet: Wallet = {
  id: 'wallet_1',
  tenant_id: 'tenant_1',
  balance: 5000,
  currency: 'usd',
  credit_limit: 10000,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-06-01T00:00:00Z',
};

const mockUsageSummary: UsageSummary[] = [
  {
    metric_name: 'api_calls',
    unit: 'calls',
    total_quantity: 1500,
    period_start: '2024-06-01T00:00:00Z',
    period_end: '2024-07-01T00:00:00Z',
  },
];

describe('BillingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock returns
    vi.mocked(billingApi.getSubscription).mockResolvedValue({ data: mockSubscription } as any);
    vi.mocked(billingApi.listInvoices).mockResolvedValue({
      data: mockInvoices,
      meta: { total: 1, page: 1, per_page: 10, has_more: false },
      links: { self: '' },
    } as any);
    vi.mocked(billingApi.getWallet).mockResolvedValue({ data: mockWallet } as any);
    vi.mocked(billingApi.getUsageSummary).mockResolvedValue({ data: mockUsageSummary } as any);
  });

  it('renders the billing page heading and description', () => {
    render(<BillingPage />);
    expect(screen.getByRole('heading', { name: /billing/i })).toBeInTheDocument();
    expect(screen.getByText(/manage your subscription/i)).toBeInTheDocument();
  });

  it('renders subscription tab content and calls billing API on mount', async () => {
    render(<BillingPage />);
    // Verify API was called on mount
    expect(billingApi.getSubscription).toHaveBeenCalledTimes(1);
    // Wait for subscription content to render
    await waitFor(() => {
      expect(screen.getByText(/pro plan/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/professional plan/i)).toBeInTheDocument();
    // Price should be shown (2900 cents = $2,900 formatted by Intl.NumberFormat)
    expect(screen.getByText(/\$2,900/)).toBeInTheDocument();
    // Plan features should render
    expect(screen.getByText(/unlimited contacts/i)).toBeInTheDocument();
    expect(screen.getByText(/email campaigns/i)).toBeInTheDocument();
  });

  it('shows loading skeleton while subscription is loading', () => {
    // Make the API never resolve to see skeleton
    vi.mocked(billingApi.getSubscription).mockImplementation(() => new Promise(() => {}));
    render(<BillingPage />);
    // The skeleton renders inside the card - verify the component still renders heading
    expect(screen.getByRole('heading', { name: /billing/i })).toBeInTheDocument();
    // The subscription content should not be present (still loading)
    expect(screen.queryByText(/pro plan/i)).not.toBeInTheDocument();
  });

  it('renders invoices tab content', async () => {
    const user = userEvent.setup();
    render(<BillingPage />);

    // Click on Invoices tab
    const invoicesTab = screen.getByRole('tab', { name: /invoices/i });
    await user.click(invoicesTab);

    // API should be called for invoices
    expect(billingApi.listInvoices).toHaveBeenCalled();

    // Wait for invoice data to render
    await waitFor(() => {
      expect(screen.getByText('INV-001')).toBeInTheDocument();
    });
  });

  it('renders wallet tab', async () => {
    const user = userEvent.setup();
    render(<BillingPage />);

    // Click on Wallet tab
    const walletTab = screen.getByRole('tab', { name: /wallet/i });
    await user.click(walletTab);

    // API should be called for wallet and usage
    expect(billingApi.getWallet).toHaveBeenCalled();
    expect(billingApi.getUsageSummary).toHaveBeenCalled();

    // Wait for wallet balance to render (5000 = $5,000)
    await waitFor(() => {
      expect(screen.getByText(/\$5,000/)).toBeInTheDocument();
    });
    expect(screen.getByText(/available credit/i)).toBeInTheDocument();
  });

  it('shows "No Active Subscription" when no subscription exists', async () => {
    vi.mocked(billingApi.getSubscription).mockResolvedValue({ data: null as any } as any);
    render(<BillingPage />);
    await waitFor(() => {
      expect(screen.getByText(/no active subscription/i)).toBeInTheDocument();
    });
  });

  it('renders the subscription status badge', async () => {
    const activeSub: Subscription = {
      ...mockSubscription,
      status: 'active',
    };
    vi.mocked(billingApi.getSubscription).mockResolvedValue({ data: activeSub } as any);
    render(<BillingPage />);
    await waitFor(() => {
      expect(screen.getByText(/active/i)).toBeInTheDocument();
    });
  });

  it('renders cancel subscription button', async () => {
    render(<BillingPage />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /cancel subscription/i })).toBeInTheDocument();
    });
  });

  it('renders manage plan link', async () => {
    render(<BillingPage />);
    await waitFor(() => {
      const manageLink = screen.getByRole('link', { name: /manage plan/i });
      expect(manageLink).toBeInTheDocument();
      expect(manageLink).toHaveAttribute('href', '/billing/subscription');
    });
  });
});
