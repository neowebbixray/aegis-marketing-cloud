'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Plus,
  FileText,
  Download,
  Send,
  RefreshCw,
  Calendar,
  Clock,
  Loader2,
  MoreHorizontal,
  Trash2,
  Eye,
  ChevronLeft,
  ChevronRight,
  BarChart3,
  Mail,
  FileSpreadsheet,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import { Input } from '@/components/atoms/input';
import { Label } from '@/components/atoms/label';
import { Separator } from '@/components/atoms/separator';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/molecules/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/molecules/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/molecules/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/molecules/dialog';
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
import { formatDate, formatDateTime } from '@/lib/utils';
import type { Report } from '@/lib/api/analytics';

// ─── Helpers ────────────────────────────────────────────────

const reportTypeIcons: Record<string, React.ElementType> = {
  summary: BarChart3,
  email: Mail,
  csv: FileSpreadsheet,
  pdf: FileText,
  xlsx: FileSpreadsheet,
};

const reportTypeColors: Record<string, string> = {
  summary: 'bg-primary/10 text-primary',
  email: 'bg-accent/10 text-accent-foreground',
  csv: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100',
  pdf: 'bg-destructive/10 text-destructive',
  xlsx: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-100',
};

const frequencyLabels: Record<string, string> = {
  daily: 'Every day',
  weekly: 'Every week',
  monthly: 'Every month',
};

// ─── Create Report Dialog ───────────────────────────────────

interface CreateReportForm {
  name: string;
  description: string;
  type: string;
  frequency: string;
  recipients: string;
}

function CreateReportDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<CreateReportForm>({
    name: '',
    description: '',
    type: 'summary',
    frequency: 'weekly',
    recipients: '',
  });
  const [creating, setCreating] = useState(false);

  const updateField = (field: keyof CreateReportForm, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreate = async () => {
    if (!form.name.trim()) {
      toast.error('Report name is required');
      return;
    }

    setCreating(true);
    try {
      await analyticsApi.createReport({
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        type: form.type,
        config: {},
        schedule: form.frequency
          ? {
              frequency: form.frequency as 'daily' | 'weekly' | 'monthly',
              recipients: form.recipients.split(',').map((r) => r.trim()).filter(Boolean),
            }
          : undefined,
      });
      toast.success('Report created successfully');
      onOpenChange(false);
      setForm({ name: '', description: '', type: 'summary', frequency: 'weekly', recipients: '' });
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create report');
    } finally {
      setCreating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create Scheduled Report</DialogTitle>
          <DialogDescription>
            Set up a recurring report that will be generated and sent automatically
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="reportName">Report Name *</Label>
            <Input
              id="reportName"
              placeholder="e.g., Weekly Marketing Summary"
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="reportDesc">Description</Label>
            <Input
              id="reportDesc"
              placeholder="Optional description"
              value={form.description}
              onChange={(e) => updateField('description', e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Report Type</Label>
              <Select value={form.type} onValueChange={(v) => updateField('type', v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="summary">Summary Report</SelectItem>
                  <SelectItem value="email">Email Report</SelectItem>
                  <SelectItem value="csv">CSV Export</SelectItem>
                  <SelectItem value="pdf">PDF Report</SelectItem>
                  <SelectItem value="xlsx">Excel Export</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Frequency</Label>
              <Select value={form.frequency} onValueChange={(v) => updateField('frequency', v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="recipients">Recipients (comma-separated emails)</Label>
            <Input
              id="recipients"
              placeholder="user@example.com, manager@example.com"
              value={form.recipients}
              onChange={(e) => updateField('recipients', e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={creating}>
            {creating ? 'Creating...' : 'Create Report'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Reports Page ───────────────────────────────────────────

export default function ReportsPage() {
  const router = useRouter();
  const [reports, setReports] = useState<Report[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [generatingIds, setGeneratingIds] = useState<Set<string>>(new Set());
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const perPage = 25;

  const fetchReports = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await analyticsApi.listReports({
        page,
        limit: perPage,
        type: typeFilter !== 'all' ? typeFilter : undefined,
      });
      setReports(res.data);
      setTotal(res.meta?.total ?? 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reports');
      setReports([]);
    } finally {
      setIsLoading(false);
    }
  }, [page, typeFilter]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleGenerateNow = async (id: string) => {
    setGeneratingIds((prev) => new Set(prev).add(id));
    try {
      const res = await analyticsApi.generateReport(id);
      toast.success('Report generated successfully');
      fetchReports();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to generate report');
    } finally {
      setGeneratingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await analyticsApi.deleteReport(id);
      toast.success('Report deleted');
      setDeleteConfirmId(null);
      fetchReports();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete report');
    }
  };

  const filteredReports = reports.filter((r) =>
    !search ||
    r.name.toLowerCase().includes(search.toLowerCase()) ||
    (r.description && r.description.toLowerCase().includes(search.toLowerCase()))
  );

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
          <p className="text-muted-foreground mt-1">
            Scheduled analytics reports and exports
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Report
        </Button>
      </div>

      {/* Search + Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Input
            placeholder="Search reports..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          value={typeFilter}
          onValueChange={(v) => {
            setTypeFilter(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="summary">Summary</SelectItem>
            <SelectItem value="email">Email</SelectItem>
            <SelectItem value="csv">CSV</SelectItem>
            <SelectItem value="pdf">PDF</SelectItem>
            <SelectItem value="xlsx">Excel</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Reports Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[250px]">Name</TableHead>
                <TableHead className="hidden md:table-cell">Type</TableHead>
                <TableHead className="hidden lg:table-cell">Schedule</TableHead>
                <TableHead className="hidden lg:table-cell">Recipients</TableHead>
                <TableHead>Last Generated</TableHead>
                <TableHead className="w-[120px]">Actions</TableHead>
                <TableHead className="w-[50px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell className="hidden md:table-cell"><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell className="hidden lg:table-cell"><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell className="hidden lg:table-cell"><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-28" /></TableCell>
                    <TableCell><Skeleton className="h-8 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-8 w-8 rounded-full" /></TableCell>
                  </TableRow>
                ))
              ) : error ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12 text-destructive">
                    Failed to load reports. Please try again.
                    <Button variant="link" onClick={fetchReports} className="ml-2">
                      Retry
                    </Button>
                  </TableCell>
                </TableRow>
              ) : filteredReports.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                    {search || typeFilter !== 'all'
                      ? 'No reports match your search'
                      : 'No reports yet. Create your first scheduled report.'}
                  </TableCell>
                </TableRow>
              ) : (
                filteredReports.map((report) => {
                  const ReportIcon = reportTypeIcons[report.type] || FileText;
                  const typeColor = reportTypeColors[report.type] || 'bg-muted text-muted-foreground';

                  return (
                    <TableRow key={report.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className={`rounded-lg p-2 ${typeColor}`}>
                            <ReportIcon className="h-4 w-4" />
                          </div>
                          <div>
                            <p className="font-medium">{report.name}</p>
                            {report.description && (
                              <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                {report.description}
                              </p>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="hidden md:table-cell">
                        <Badge variant="outline" className={typeColor}>
                          {report.type.charAt(0).toUpperCase() + report.type.slice(1)}
                        </Badge>
                      </TableCell>
                      <TableCell className="hidden lg:table-cell">
                        {report.schedule ? (
                          <div className="flex items-center gap-1 text-sm">
                            <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                            {frequencyLabels[report.schedule.frequency] || report.schedule.frequency}
                          </div>
                        ) : (
                          <span className="text-sm text-muted-foreground">Manual only</span>
                        )}
                      </TableCell>
                      <TableCell className="hidden lg:table-cell">
                        {report.schedule?.recipients && report.schedule.recipients.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {report.schedule.recipients.slice(0, 2).map((email) => (
                              <Badge key={email} variant="secondary" className="text-xs">
                                {email}
                              </Badge>
                            ))}
                            {report.schedule.recipients.length > 2 && (
                              <Badge variant="outline" className="text-xs">
                                +{report.schedule.recipients.length - 2}
                              </Badge>
                            )}
                          </div>
                        ) : (
                          <span className="text-sm text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {report.last_generated_at
                          ? formatDateTime(report.last_generated_at)
                          : 'Never'}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleGenerateNow(report.id)}
                          disabled={generatingIds.has(report.id)}
                        >
                          {generatingIds.has(report.id) ? (
                            <><Loader2 className="mr-1 h-3 w-3 animate-spin" /> Generating...</>
                          ) : (
                            <><RefreshCw className="mr-1 h-3 w-3" /> Generate</>
                          )}
                        </Button>
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon-sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <DropdownMenuItem>
                              <Eye className="mr-2 h-4 w-4" />
                              View Report
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Download className="mr-2 h-4 w-4" />
                              Download
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => setDeleteConfirmId(report.id)}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination */}
      {!isLoading && !error && total > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing page {page} of {totalPages} ({total} total)
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!deleteConfirmId}
        onOpenChange={(open) => !open && setDeleteConfirmId(null)}
      >
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Delete Report</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this scheduled report? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteConfirmId && handleDelete(deleteConfirmId)}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Report Dialog */}
      <CreateReportDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreated={fetchReports}
      />
    </div>
  );
}
