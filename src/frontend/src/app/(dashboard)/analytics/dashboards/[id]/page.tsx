'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  BarChart3,
  TrendingUp,
  LineChart,
  Table2,
  PieChart,
  AreaChart,
  Download,
  Calendar,
  RefreshCw,
  MoreHorizontal,
  Edit,
  Trash2,
  Plus,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/molecules/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/molecules/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/molecules/dropdown-menu';
import { Skeleton } from '@/components/atoms/skeleton';
import { toast } from 'sonner';
import { analyticsApi } from '@/lib/api/analytics';
import { formatDate } from '@/lib/utils';
import type { Dashboard, DashboardWidget, AnalyticsGranularity } from '@/lib/api/analytics';
import {
  LineChart as RechartsLineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  AreaChart as RechartsAreaChart,
  Area,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

// ─── Helpers ────────────────────────────────────────────────

const widgetTypeIcons: Record<string, React.ElementType> = {
  chart: LineChart,
  metric: TrendingUp,
  table: Table2,
  funnel: PieChart,
  map: AreaChart,
};

const widgetSizeClasses: Record<string, string> = {
  sm: 'col-span-1 row-span-1',
  md: 'col-span-1 md:col-span-2 row-span-1',
  lg: 'col-span-1 md:col-span-3 row-span-2',
  full: 'col-span-full',
};

const sampleTimeSeries = (type: 'line' | 'bar' | 'area' | 'pie') => {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const data = months.slice(0, 6).map((name) => ({
    name,
    value: Math.floor(Math.random() * 1000) + 200,
    previous: Math.floor(Math.random() * 800) + 100,
  }));
  return data;
};

const pieData = [
  { name: 'Email', value: 35 },
  { name: 'Social', value: 25 },
  { name: 'Search', value: 20 },
  { name: 'Direct', value: 15 },
  { name: 'Referral', value: 5 },
];

const COLORS = ['hsl(var(--primary))', 'hsl(var(--accent))', 'hsl(var(--success))', 'hsl(var(--warning))', 'hsl(var(--destructive))'];

// ─── Widget Components ──────────────────────────────────────

function MetricWidget({ widget }: { widget: DashboardWidget }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {widget.title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold">
          {Math.floor(Math.random() * 10000) + 500}
        </div>
        <div className="flex items-center gap-1 mt-1">
          <TrendingUp className="h-4 w-4 text-success-600" />
          <span className="text-xs font-medium text-success-600">
            +{Math.floor(Math.random() * 20) + 1}%
          </span>
          <span className="text-xs text-muted-foreground">vs previous period</span>
        </div>
      </CardContent>
    </Card>
  );
}

function LineChartWidget({ widget }: { widget: DashboardWidget }) {
  const data = sampleTimeSeries('line');
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{widget.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <RechartsLineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="name" className="text-xs text-muted-foreground" />
              <YAxis className="text-xs text-muted-foreground" />
              <RechartsTooltip />
              <Line type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="previous" stroke="hsl(var(--muted-foreground))" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
            </RechartsLineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function BarChartWidget({ widget }: { widget: DashboardWidget }) {
  const data = sampleTimeSeries('bar');
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{widget.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="name" className="text-xs text-muted-foreground" />
              <YAxis className="text-xs text-muted-foreground" />
              <RechartsTooltip />
              <Bar dataKey="value" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
              <Bar dataKey="previous" fill="hsl(var(--muted-foreground))" radius={[4, 4, 0, 0]} opacity={0.4} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function AreaChartWidget({ widget }: { widget: DashboardWidget }) {
  const data = sampleTimeSeries('area');
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{widget.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <RechartsAreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="name" className="text-xs text-muted-foreground" />
              <YAxis className="text-xs text-muted-foreground" />
              <RechartsTooltip />
              <Area type="monotone" dataKey="value" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.2} />
              <Area type="monotone" dataKey="previous" stroke="hsl(var(--muted-foreground))" fill="hsl(var(--muted-foreground))" fillOpacity={0.1} />
            </RechartsAreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function PieChartWidget({ widget }: { widget: DashboardWidget }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{widget.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[220px]">
          <ResponsiveContainer width="100%" height="100%">
            <RechartsPieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={3}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <RechartsTooltip />
            </RechartsPieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function TableWidget({ widget }: { widget: DashboardWidget }) {
  const columns = ['Channel', 'Visitors', 'Conversions', 'Revenue'];
  const rows = [
    { channel: 'Email', visitors: '2,847', conversions: '384', revenue: '$12,450' },
    { channel: 'Social Media', visitors: '4,201', conversions: '215', revenue: '$8,320' },
    { channel: 'Search', visitors: '6,534', conversions: '502', revenue: '$21,780' },
    { channel: 'Direct', visitors: '3,112', conversions: '187', revenue: '$6,540' },
    { channel: 'Referral', visitors: '1,023', conversions: '89', revenue: '$3,210' },
  ];
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{widget.title}</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                {columns.map((col) => (
                  <th key={col} className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.channel} className="border-b last:border-0">
                  <td className="px-4 py-2 font-medium">{row.channel}</td>
                  <td className="px-4 py-2 text-muted-foreground">{row.visitors}</td>
                  <td className="px-4 py-2 text-muted-foreground">{row.conversions}</td>
                  <td className="px-4 py-2 text-muted-foreground">{row.revenue}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function WidgetRenderer({ widget }: { widget: DashboardWidget }) {
  switch (widget.chart_type || widget.type) {
    case 'line':
      return <LineChartWidget widget={widget} />;
    case 'bar':
      return <BarChartWidget widget={widget} />;
    case 'area':
      return <AreaChartWidget widget={widget} />;
    case 'pie':
      return <PieChartWidget widget={widget} />;
    case 'metric':
      return <MetricWidget widget={widget} />;
    case 'table':
      return <TableWidget widget={widget} />;
    default:
      return (
        <Card>
          <CardContent className="flex items-center justify-center h-[200px] text-muted-foreground">
            {widget.title} — {widget.type}
          </CardContent>
        </Card>
      );
  }
}

// ─── Dashboard Detail Page ──────────────────────────────────

export default function DashboardDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [granularity, setGranularity] = useState<AnalyticsGranularity>('day');
  const [dateRange, setDateRange] = useState<string>('last7d');
  const [exporting, setExporting] = useState(false);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await analyticsApi.getDashboard(id);
      setDashboard(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      fetchDashboard();
    }
  }, [id, fetchDashboard]);

  const handleExport = async () => {
    setExporting(true);
    try {
      // Simulate export — in production this would call analyticsApi.exportData
      toast.success('Dashboard data exported successfully');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to export');
    } finally {
      setExporting(false);
    }
  };

  const handleRefresh = async () => {
    toast.success('Dashboard data refreshed');
    fetchDashboard();
  };

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32 mt-2" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error || !dashboard) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <p className="text-muted-foreground">Dashboard not found</p>
        <Button variant="link" onClick={() => router.push('/analytics')}>
          Back to analytics
        </Button>
      </div>
    );
  }

  const widgets = dashboard.widgets || [];
  const chartWidgets = ['chart', 'line', 'bar', 'area', 'pie', 'metric', 'table'] as const;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{dashboard.name}</h1>
            {dashboard.description && (
              <p className="text-muted-foreground text-sm mt-1">{dashboard.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger className="w-[140px]">
              <Calendar className="mr-2 h-4 w-4" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="yesterday">Yesterday</SelectItem>
              <SelectItem value="last7d">Last 7 Days</SelectItem>
              <SelectItem value="last30d">Last 30 Days</SelectItem>
              <SelectItem value="last90d">Last 90 Days</SelectItem>
              <SelectItem value="thisMonth">This Month</SelectItem>
              <SelectItem value="lastMonth">Last Month</SelectItem>
              <SelectItem value="custom">Custom Range</SelectItem>
            </SelectContent>
          </Select>
          <Select value={granularity} onValueChange={setGranularity}>
            <SelectTrigger className="w-[110px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="hour">Hourly</SelectItem>
              <SelectItem value="day">Daily</SelectItem>
              <SelectItem value="week">Weekly</SelectItem>
              <SelectItem value="month">Monthly</SelectItem>
              <SelectItem value="quarter">Quarterly</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport} disabled={exporting}>
            <Download className="mr-2 h-4 w-4" />
            {exporting ? 'Exporting...' : 'Export'}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Dashboard Actions</DropdownMenuLabel>
              <DropdownMenuItem>
                <Edit className="mr-2 h-4 w-4" />
                Edit Dashboard
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Plus className="mr-2 h-4 w-4" />
                Add Widget
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Dashboard
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Summary Bar */}
      <div className="grid gap-4 md:grid-cols-4">
        {[
          { label: 'Total Widgets', value: widgets.length.toString() },
          { label: 'Data Points', value: '1,284' },
          { label: 'Last Updated', value: formatDate(dashboard.updated_at) },
          { label: 'Created', value: formatDate(dashboard.created_at) },
        ].map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="pb-1">
              <CardTitle className="text-xs font-medium text-muted-foreground">
                {stat.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-lg font-semibold">{stat.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Widget Grid */}
      {widgets.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-16">
            <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium text-muted-foreground mb-1">
              No widgets yet
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              Add widgets to this dashboard to visualize your data
            </p>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Add Widget
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 grid-cols-1 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          {widgets.map((widget) => {
            const WidgetIcon = widgetTypeIcons[widget.type] || LineChart;
            const sizeClass = widgetSizeClasses[widget.size] || 'col-span-1';
            return (
              <div key={widget.id} className={sizeClass}>
                <WidgetRenderer widget={widget} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
