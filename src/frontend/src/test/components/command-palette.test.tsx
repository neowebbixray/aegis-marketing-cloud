import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CommandPalette } from '@/components/features/command-palette';

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

describe('CommandPalette', () => {
  beforeEach(() => {
    mockPush.mockClear();
    // Reset window.location mock if any
  });

  it('renders without crashing', () => {
    render(<CommandPalette />);
    // The dialog should not be visible initially
    expect(screen.queryByPlaceholderText(/search/i)).not.toBeInTheDocument();
  });

  it('opens when Cmd+K is pressed', async () => {
    const user = userEvent.setup();
    render(<CommandPalette />);

    // Simulate Cmd+K
    await user.keyboard('{Meta>}k{/Meta}');

    const input = screen.getByPlaceholderText(/search/i);
    expect(input).toBeInTheDocument();
  });

  it('opens when Ctrl+K is pressed', async () => {
    const user = userEvent.setup();
    render(<CommandPalette />);

    await user.keyboard('{Control>}k{/Control}');

    const input = screen.getByPlaceholderText(/search/i);
    expect(input).toBeInTheDocument();
  });

  it('closes when Escape is pressed', async () => {
    const user = userEvent.setup();
    render(<CommandPalette />);

    // Open first
    await user.keyboard('{Meta>}k{/Meta}');
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();

    // Close with Escape
    await user.keyboard('{Escape}');
    expect(screen.queryByPlaceholderText(/search/i)).not.toBeInTheDocument();
  });

  it('filters results based on search input', async () => {
    const user = userEvent.setup();
    render(<CommandPalette />);

    // Open command palette
    await user.keyboard('{Meta>}k{/Meta}');

    // Type a search query
    const input = screen.getByPlaceholderText(/search/i);
    await user.type(input, 'contacts');

    // Should show CRM > Contacts navigation item
    expect(screen.getByText(/CRM.*Contacts/i)).toBeInTheDocument();

    // Should not show unrelated items like Settings
    expect(screen.queryByText(/Settings/i)).not.toBeInTheDocument();
  });

  it('navigates when a navigation item is clicked', async () => {
    const user = userEvent.setup();
    render(<CommandPalette />);

    // Open command palette
    await user.keyboard('{Meta>}k{/Meta}');

    // Type to filter
    const input = screen.getByPlaceholderText(/search/i);
    await user.type(input, 'dashboard');

    // Find the dashboard option by role (avoid empty-state text conflict)
    const dashboardItem = screen.getByRole('option', { name: /dashboard/i });
    await user.click(dashboardItem);

    // Should have navigated to /dashboard
    expect(mockPush).toHaveBeenCalledWith('/dashboard');
  });

  it('shows empty state when no results match', async () => {
    const user = userEvent.setup();
    render(<CommandPalette />);

    // Open command palette
    await user.keyboard('{Meta>}k{/Meta}');

    // Type something that won't match anything
    const input = screen.getByPlaceholderText(/search/i);
    await user.type(input, 'zzzznotfound');

    // Should show no results message
    expect(screen.getByText(/no results/i)).toBeInTheDocument();
  });

  it('shows hint text when search is empty', async () => {
    const user = userEvent.setup();
    render(<CommandPalette />);

    await user.keyboard('{Meta>}k{/Meta}');

    expect(screen.getByText(/start typing/i)).toBeInTheDocument();
  });

  it('renders action items with shortcuts', async () => {
    const user = userEvent.setup();
    render(<CommandPalette />);

    await user.keyboard('{Meta>}k{/Meta}');

    // Type to find new contact action
    const input = screen.getByPlaceholderText(/search/i);
    await user.type(input, 'new contact');

    // Should show the action option (not the empty-state text)
    const newContact = screen.getByRole('option', { name: /new contact/i });
    expect(newContact).toBeInTheDocument();
    expect(newContact).toHaveTextContent('C'); // shortcut
  });
});
