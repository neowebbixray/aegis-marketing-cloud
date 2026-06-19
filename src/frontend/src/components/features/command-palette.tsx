'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
} from '@/components/molecules/command';
import {
  LayoutDashboard,
  Users,
  Briefcase,
  GitBranch,
  Megaphone,
  SearchIcon,
  Share2,
  Brain,
  BarChart3,
  Settings,
  PlusCircle,
  FileText,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';

// ─── Types ─────────────────────────────────────────────────

interface CommandItemBase {
  id: string;
  label: string;
  keywords: string[];
  icon: LucideIcon;
}

interface NavigationItem extends CommandItemBase {
  type: 'navigation';
  href: string;
}

interface ActionItem extends CommandItemBase {
  type: 'action';
  action: () => void;
  shortcut?: string;
}

type CommandItemType = NavigationItem | ActionItem;

interface CommandCategory {
  label: string;
  items: CommandItemType[];
}

// ─── Fuzzy Search ──────────────────────────────────────────

function fuzzyMatch(query: string, text: string): boolean {
  if (!query) return true;
  const lowerQuery = query.toLowerCase();
  const lowerText = text.toLowerCase();

  // Exact substring match
  if (lowerText.includes(lowerQuery)) return true;

  // Character-by-character fuzzy match
  let qi = 0;
  for (let ti = 0; ti < lowerText.length && qi < lowerQuery.length; ti++) {
    if (lowerText[ti] === lowerQuery[qi]) {
      qi++;
    }
  }
  return qi === lowerQuery.length;
}

function scoreFuzzyMatch(query: string, item: CommandItemType): number {
  if (!query) return 0;
  const lowerQuery = query.toLowerCase();
  const lowerLabel = item.label.toLowerCase();

  // Exact match = highest score
  if (lowerLabel === lowerQuery) return 100;

  // Starts with query
  if (lowerLabel.startsWith(lowerQuery)) return 80;

  // Contains query as substring
  if (lowerLabel.includes(lowerQuery)) return 60;

  // Keyword match
  for (const kw of item.keywords) {
    if (kw.toLowerCase().includes(lowerQuery)) return 40;
    if (fuzzyMatch(query, kw)) return 30;
  }

  // Fuzzy label match
  if (fuzzyMatch(query, lowerLabel)) return 20;

  return 0;
}

// ─── Categories & Items ────────────────────────────────────

const navigationCategories: CommandCategory[] = [
  {
    label: 'Navigation — Main',
    items: [
      {
        id: 'nav-dashboard',
        type: 'navigation',
        label: 'Dashboard',
        href: '/dashboard',
        keywords: ['home', 'overview', 'analytics'],
        icon: LayoutDashboard,
      },
    ],
  },
  {
    label: 'Navigation — CRM',
    items: [
      {
        id: 'nav-contacts',
        type: 'navigation',
        label: 'CRM > Contacts',
        href: '/crm/contacts',
        keywords: ['people', 'leads', 'customers', 'address book'],
        icon: Users,
      },
      {
        id: 'nav-deals',
        type: 'navigation',
        label: 'CRM > Deals',
        href: '/crm/deals',
        keywords: ['opportunities', 'sales', 'pipeline deals'],
        icon: Briefcase,
      },
      {
        id: 'nav-pipelines',
        type: 'navigation',
        label: 'CRM > Pipelines',
        href: '/crm/pipelines',
        keywords: ['sales pipeline', 'stages', 'workflow'],
        icon: GitBranch,
      },
    ],
  },
  {
    label: 'Navigation — Marketing',
    items: [
      {
        id: 'nav-campaigns',
        type: 'navigation',
        label: 'Marketing > Campaigns',
        href: '/marketing/campaigns',
        keywords: ['email', 'marketing automation', 'broadcast'],
        icon: Megaphone,
      },
      {
        id: 'nav-seo',
        type: 'navigation',
        label: 'Marketing > SEO',
        href: '/marketing/seo',
        keywords: ['search', 'keywords', 'ranking', 'optimization'],
        icon: SearchIcon,
      },
      {
        id: 'nav-social',
        type: 'navigation',
        label: 'Marketing > Social',
        href: '/marketing/social',
        keywords: ['social media', 'posts', 'engagement'],
        icon: Share2,
      },
    ],
  },
  {
    label: 'Navigation — AI & Analytics',
    items: [
      {
        id: 'nav-ai-suite',
        type: 'navigation',
        label: 'AI Suite',
        href: '/ai-suite',
        keywords: ['artificial intelligence', 'agents', 'chat', 'generate'],
        icon: Brain,
      },
      {
        id: 'nav-analytics',
        type: 'navigation',
        label: 'Analytics',
        href: '/analytics',
        keywords: ['reports', 'metrics', 'dashboard', 'insights'],
        icon: BarChart3,
      },
      {
        id: 'nav-settings',
        type: 'navigation',
        label: 'Settings',
        href: '/settings',
        keywords: ['preferences', 'configuration', 'profile', 'account'],
        icon: Settings,
      },
    ],
  },
];

const actionCategory: CommandCategory = {
  label: 'Actions',
  items: [
    {
      id: 'action-new-contact',
      type: 'action',
      label: 'New Contact',
      keywords: ['create contact', 'add person', 'new lead'],
      icon: PlusCircle,
      action: () => {
        // Will navigate to contacts page — the page itself handles the create modal
        window.location.href = '/crm/contacts?new=true';
      },
      shortcut: 'C',
    },
    {
      id: 'action-new-deal',
      type: 'action',
      label: 'New Deal',
      keywords: ['create deal', 'add opportunity', 'new sale'],
      icon: PlusCircle,
      action: () => {
        window.location.href = '/crm/deals?new=true';
      },
      shortcut: 'D',
    },
    {
      id: 'action-new-campaign',
      type: 'action',
      label: 'New Campaign',
      keywords: ['create campaign', 'new email', 'marketing campaign'],
      icon: Megaphone,
      action: () => {
        window.location.href = '/marketing/campaigns?new=true';
      },
      shortcut: 'M',
    },
    {
      id: 'action-create-report',
      type: 'action',
      label: 'Create Report',
      keywords: ['new report', 'analytics report', 'export data'],
      icon: FileText,
      action: () => {
        window.location.href = '/analytics/reports?new=true';
      },
      shortcut: 'R',
    },
    {
      id: 'action-generate-content',
      type: 'action',
      label: 'Generate Content',
      keywords: ['ai content', 'writing', 'blog post', 'copywriting', 'draft'],
      icon: Sparkles,
      action: () => {
        window.location.href = '/ai-suite?generate=true';
      },
      shortcut: 'G',
    },
  ],
};

// ─── Quick Search (dynamic — shows recent pages or contextual matches) ──
// For now, this is a placeholder that could be extended with recent items.

// ─── Flatten all items with category context ───────────────

function getAllItems(): Array<{ category: string; item: CommandItemType }> {
  const all: Array<{ category: string; item: CommandItemType }> = [];

  for (const cat of navigationCategories) {
    for (const item of cat.items) {
      all.push({ category: cat.label, item });
    }
  }

  for (const item of actionCategory.items) {
    all.push({ category: actionCategory.label, item });
  }

  return all;
}

// ─── Component ─────────────────────────────────────────────

declare global {
  interface Window {
    __commandPaletteOpen?: boolean;
  }
}

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const [selectedIndex, setSelectedIndex] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Get filtered and scored items
  const filteredItems = React.useMemo(() => {
    const allItems = getAllItems();
    const scored = allItems
      .map(({ category, item }) => ({
        category,
        item,
        score: scoreFuzzyMatch(search, item),
      }))
      .filter((entry) => entry.score > 0);

    // Sort by score descending
    scored.sort((a, b) => b.score - a.score);

    // Group by category
    const groups: Array<{ category: string; items: typeof scored }> = [];
    const seenCategories = new Set<string>();
    for (const entry of scored) {
      if (!seenCategories.has(entry.category)) {
        seenCategories.add(entry.category);
        groups.push({ category: entry.category, items: [] });
      }
      groups[groups.length - 1].items.push(entry);
    }

    return groups;
  }, [search]);

  // Reset selected index when search changes
  React.useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  // Keyboard shortcut
  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === 'Escape' && open) {
        setOpen(false);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [open]);

  // Focus input when dialog opens
  React.useEffect(() => {
    if (open) {
      // Small delay to allow dialog animation
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [open]);

  const handleSelect = React.useCallback(
    (entry: { category: string; item: CommandItemType }) => {
      setOpen(false);
      setSearch('');

      if (entry.item.type === 'navigation') {
        router.push((entry.item as NavigationItem).href);
      } else {
        (entry.item as ActionItem).action();
      }
    },
    [router]
  );

  // Keyboard navigation within the list
  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, getAllItems().length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        // Find the nth visible item
        const allVisible = filteredItems.flatMap((g) => g.items);
        const target = allVisible[selectedIndex];
        if (target) {
          handleSelect(target);
        }
      }
    },
    [filteredItems, selectedIndex, handleSelect]
  );

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <div cmdk-input-wrapper="">
        <CommandInput
          ref={inputRef}
          placeholder="Search pages, actions, and more..."
          value={search}
          onValueChange={setSearch}
          onKeyDown={handleKeyDown}
        />
      </div>
      <CommandList>
        <CommandEmpty>
          {search ? (
            <span>
              No results for &ldquo;{search}&rdquo;
            </span>
          ) : (
            <span>Start typing to search...</span>
          )}
        </CommandEmpty>

        {filteredItems.map((group) => (
          <CommandGroup key={group.category} heading={group.category}>
            {group.items.map((entry) => {
              const Icon = entry.item.icon;
              const isSelected =
                filteredItems
                  .flatMap((g) => g.items)
                  .indexOf(entry) === selectedIndex;

              return (
                <CommandItem
                  key={entry.item.id}
                  onSelect={() => handleSelect(entry)}
                  data-selected={isSelected || undefined}
                  aria-selected={isSelected}
                >
                  <Icon className="mr-2 h-4 w-4" />
                  <span>{entry.item.label}</span>
                  {entry.item.type === 'action' && entry.item.shortcut && (
                    <CommandShortcut>
                      {entry.item.shortcut}
                    </CommandShortcut>
                  )}
                </CommandItem>
              );
            })}
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  );
}
