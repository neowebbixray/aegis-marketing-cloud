'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  BookOpen,
  Plus,
  Search,
  Filter,
  Upload,
  FileText,
  File,
  FileSpreadsheet,
  FileJson,
  Globe,
  Trash2,
  MoreHorizontal,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Database,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  ExternalLink,
  Download,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import { Input } from '@/components/atoms/input';
import { Label } from '@/components/atoms/label';
import { Textarea } from '@/components/atoms/textarea';
import { Separator } from '@/components/atoms/separator';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/molecules/card';
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/molecules/dropdown-menu';
import { Skeleton } from '@/components/atoms/skeleton';
import { toast } from 'sonner';
import { knowledgeApi } from '@/lib/api/knowledge';
import { formatDateTime, truncate } from '@/lib/utils';
import type { KnowledgeDocument, DocumentStatus, SearchResult } from '@/lib/api/knowledge';

// ─── Constants ────────────────────────────────────────────────

const statusConfig: Record<DocumentStatus, { label: string; icon: React.ElementType; className: string }> = {
  processing: { label: 'Processing', icon: Clock, className: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-100' },
  indexed: { label: 'Indexed', icon: CheckCircle2, className: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100' },
  failed: { label: 'Failed', icon: XCircle, className: 'bg-destructive/10 text-destructive' },
};

const contentTypeIcons: Record<string, React.ElementType> = {
  pdf: FileText,
  docx: FileText,
  txt: File,
  md: FileText,
  html: Globe,
  csv: FileSpreadsheet,
  json: FileJson,
};

function getFileIcon(contentType: string): React.ElementType {
  const ext = contentType.toLowerCase();
  for (const [key, icon] of Object.entries(contentTypeIcons)) {
    if (ext.includes(key)) return icon;
  }
  return File;
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ─── Upload Dialog ────────────────────────────────────────────

function UploadDocumentDialog({
  open,
  onOpenChange,
  onUploaded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUploaded: () => void;
}) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async () => {
    if (!title.trim()) {
      toast.error('Title is required');
      return;
    }

    setUploading(true);
    try {
      await knowledgeApi.uploadDocument({
        file: file || undefined,
        title: title.trim(),
        description: description.trim() || undefined,
        source_url: sourceUrl.trim() || undefined,
        tags: tags.trim() ? tags.split(',').map((t) => t.trim()) : undefined,
      });
      toast.success('Document uploaded successfully');
      onOpenChange(false);
      setTitle('');
      setDescription('');
      setTags('');
      setSourceUrl('');
      setFile(null);
      onUploaded();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to upload document');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Upload Document</DialogTitle>
          <DialogDescription>
            Add a document to your knowledge base
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="upload-file">File (optional)</Label>
            <Input
              id="upload-file"
              type="file"
              accept=".pdf,.docx,.txt,.md,.html,.csv"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <p className="text-xs text-muted-foreground">
              Supported: PDF, DOCX, TXT, MD, HTML, CSV
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="upload-title">Title *</Label>
            <Input
              id="upload-title"
              placeholder="Document title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="upload-desc">Description</Label>
            <Textarea
              id="upload-desc"
              placeholder="Brief description of the document"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="upload-tags">Tags (comma-separated)</Label>
            <Input
              id="upload-tags"
              placeholder="e.g., marketing, seo, content"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="upload-url">Source URL (optional)</Label>
            <Input
              id="upload-url"
              placeholder="https://example.com/document"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleUpload} disabled={uploading || !title.trim()}>
            {uploading ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Uploading...</>
            ) : (
              <><Upload className="mr-2 h-4 w-4" /> Upload</>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Knowledge Base Page ─────────────────────────────────────

export default function KnowledgeBasePage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [tagFilter, setTagFilter] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 20;

  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Semantic search
  const [semanticQuery, setSemanticQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [showSearchResults, setShowSearchResults] = useState(false);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, unknown> = {
        page,
        limit: perPage,
      };
      if (statusFilter !== 'all') params.status = statusFilter;
      if (search) params.search = search;
      if (tagFilter) params.tags = tagFilter.split(',').map((t) => t.trim());

      const res = await knowledgeApi.listDocuments(params as Parameters<typeof knowledgeApi.listDocuments>[0]);
      setDocuments(res.data);
      setTotal(res.meta.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, search, tagFilter]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleSearch = async () => {
    if (!semanticQuery.trim()) return;
    setSearching(true);
    setShowSearchResults(true);
    try {
      const res = await knowledgeApi.search({
        query: semanticQuery.trim(),
        limit: 5,
      });
      setSearchResults(res.data || []);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Search failed');
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await knowledgeApi.deleteDocument(id);
      toast.success('Document deleted');
      setDeleteConfirmId(null);
      fetchDocuments();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete document');
    }
  };

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <BookOpen className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Knowledge Base</h1>
            <p className="text-muted-foreground mt-1">
              Store, search, and manage your documents and knowledge
            </p>
          </div>
        </div>
        <Button onClick={() => setUploadDialogOpen(true)}>
          <Upload className="mr-2 h-4 w-4" />
          Upload Document
        </Button>
      </div>

      {/* Semantic Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Ask a question about your documents..."
                className="pl-9"
                value={semanticQuery}
                onChange={(e) => setSemanticQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSearch();
                }}
              />
            </div>
            <Button onClick={handleSearch} disabled={searching || !semanticQuery.trim()}>
              {searching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              Search
            </Button>
          </div>

          {/* Search Results */}
          {showSearchResults && (
            <div className="mt-4">
              {searching ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : searchResults.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No results found for your query
                </p>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">
                    Top {searchResults.length} results
                  </p>
                  {searchResults.map((result, idx) => (
                    <div
                      key={`${result.document_id}-${idx}`}
                      className="flex items-start gap-3 p-3 rounded-lg border hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => router.push(`/knowledge/${result.document_id}`)}
                    >
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                        <FileText className="h-4 w-4 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{result.document_title}</p>
                        <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                          {result.snippet}
                        </p>
                      </div>
                      <Badge variant="secondary" className="flex-shrink-0">
                        {(result.score * 100).toFixed(0)}% match
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Search + Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            className="pl-9"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          value={statusFilter}
          onValueChange={(v) => {
            setStatusFilter(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[150px]">
            <Filter className="mr-2 h-4 w-4" />
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="indexed">Indexed</SelectItem>
            <SelectItem value="processing">Processing</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
          </SelectContent>
        </Select>
        <Input
          placeholder="Filter by tag..."
          className="w-[180px]"
          value={tagFilter}
          onChange={(e) => {
            setTagFilter(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {/* Document List */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-10 rounded-lg" />
                  <div className="flex-1">
                    <Skeleton className="h-5 w-48" />
                    <Skeleton className="h-4 w-32 mt-1" />
                  </div>
                  <Skeleton className="h-5 w-20 rounded-full" />
                  <Skeleton className="h-5 w-24 rounded-full" />
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <Database className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
              <p className="text-destructive mb-2">Failed to load documents</p>
              <p className="text-sm text-muted-foreground mb-4">{error}</p>
              <Button variant="outline" onClick={fetchDocuments}>
                Retry
              </Button>
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-16">
              <div className="p-4 rounded-full bg-muted inline-block mb-4">
                <BookOpen className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-semibold mb-1">No documents found</h3>
              <p className="text-muted-foreground text-sm mb-4">
                {search || statusFilter !== 'all' || tagFilter
                  ? 'No documents match your filters'
                  : 'Upload your first document to get started'}
              </p>
              {(search || statusFilter !== 'all' || tagFilter) ? null : (
                <Button onClick={() => setUploadDialogOpen(true)}>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Document
                </Button>
              )}
            </div>
          ) : (
            <div className="divide-y">
              {documents.map((doc) => {
                const status = statusConfig[doc.status] || statusConfig.processing;
                const StatusIcon = status.icon;
                const FileIcon = getFileIcon(doc.content_type);

                return (
                  <div
                    key={doc.id}
                    className="flex items-center gap-4 px-6 py-4 hover:bg-muted/50 cursor-pointer transition-colors"
                    onClick={() => router.push(`/knowledge/${doc.id}`)}
                  >
                    <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <FileIcon className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{doc.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {doc.content_type} · {formatFileSize(doc.file_size)} · Uploaded {formatDateTime(doc.created_at)}
                        {doc.tags.length > 0 && ` · ${doc.tags.slice(0, 2).join(', ')}${doc.tags.length > 2 ? '...' : ''}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {doc.tags.slice(0, 2).map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs hidden sm:inline-flex">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                    <Badge variant="outline" className={`gap-1 ${status.className}`}>
                      <StatusIcon className="h-3 w-3" />
                      {status.label}
                    </Badge>
                    <div onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon-sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => router.push(`/knowledge/${doc.id}`)}>
                            <ExternalLink className="mr-2 h-4 w-4" /> View Details
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => setDeleteConfirmId(doc.id)}
                          >
                            <Trash2 className="mr-2 h-4 w-4" /> Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {total > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {totalPages} ({total} total)
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="mr-1 h-4 w-4" /> Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Upload Dialog */}
      <UploadDocumentDialog
        open={uploadDialogOpen}
        onOpenChange={setUploadDialogOpen}
        onUploaded={fetchDocuments}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!deleteConfirmId}
        onOpenChange={(open) => !open && setDeleteConfirmId(null)}
      >
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Delete Document</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this document? This action cannot be undone.
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
    </div>
  );
}
