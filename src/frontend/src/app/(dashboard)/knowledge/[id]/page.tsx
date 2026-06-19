'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  BookOpen,
  FileText,
  Globe,
  Trash2,
  RefreshCw,
  Search,
  Edit3,
  Save,
  Loader2,
  ExternalLink,
  Clock,
  CheckCircle2,
  XCircle,
  Tag,
  File,
  Calendar,
  Database,
  Link2,
  MoreHorizontal,
  Copy,
  FileSpreadsheet,
  FileJson,
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
} from '@/components/molecules/dialog';
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
import { formatDateTime } from '@/lib/utils';
import type { KnowledgeDocument, DocumentStatus, SearchResult } from '@/lib/api/knowledge';

// ─── Constants ────────────────────────────────────────────────

const statusConfig: Record<DocumentStatus, { label: string; icon: React.ElementType; className: string }> = {
  processing: { label: 'Processing', icon: Clock, className: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-100' },
  indexed: { label: 'Indexed', icon: CheckCircle2, className: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100' },
  failed: { label: 'Failed', icon: XCircle, className: 'bg-destructive/10 text-destructive' },
};

function formatFileSize(bytes?: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ─── Document Detail Page ────────────────────────────────────

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [document, setDocument] = useState<KnowledgeDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFullContent, setShowFullContent] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [reindexing, setReindexing] = useState(false);

  // Edit tags
  const [editTags, setEditTags] = useState(false);
  const [tagsInput, setTagsInput] = useState('');

  // In-document search
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  const fetchDocument = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await knowledgeApi.getDocument(id);
      setDocument(res.data);
      setTagsInput(res.data.tags?.join(', ') || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      fetchDocument();
    }
  }, [id, fetchDocument]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await knowledgeApi.search({
        query: searchQuery.trim(),
        filters: { content_type: document?.content_type },
        limit: 5,
      });
      setSearchResults(res.data || []);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleReindex = async () => {
    setReindexing(true);
    try {
      await knowledgeApi.triggerReindex();
      toast.success('Re-indexing has been triggered');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to trigger re-index');
    } finally {
      setReindexing(false);
    }
  };

  const handleDelete = async () => {
    try {
      await knowledgeApi.deleteDocument(id);
      toast.success('Document deleted');
      router.push('/knowledge');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete document');
    } finally {
      setDeleteDialogOpen(false);
    }
  };

  const handleSaveTags = async () => {
    if (!document) return;
    try {
      const newTags = tagsInput.split(',').map((t) => t.trim()).filter(Boolean);
      await knowledgeApi.updateDocument(id, { tags: newTags });
      toast.success('Tags updated');
      setEditTags(false);
      fetchDocument();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update tags');
    }
  };

  const handleCopyId = async () => {
    try {
      await navigator.clipboard.writeText(id);
      toast.success('Document ID copied to clipboard');
    } catch {
      toast.error('Failed to copy');
    }
  };

  const handleCopySourceUrl = async () => {
    if (!document?.source_url) return;
    try {
      await navigator.clipboard.writeText(document.source_url);
      toast.success('Source URL copied');
    } catch {
      toast.error('Failed to copy');
    }
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
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  // Error state
  if (error || !document) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <BookOpen className="h-12 w-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground mb-2">Document not found</p>
        <p className="text-sm text-destructive mb-4">{error}</p>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.back()}>
            Go Back
          </Button>
          <Button variant="link" onClick={() => router.push('/knowledge')}>
            Back to Knowledge Base
          </Button>
        </div>
      </div>
    );
  }

  const status = statusConfig[document.status] || statusConfig.processing;
  const StatusIcon = status.icon;

  return (
    <div className="space-y-6">
      {/* Back button + header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{document.title}</h1>
              <Badge variant="outline" className={`gap-1 ${status.className}`}>
                <StatusIcon className="h-3 w-3" />
                {status.label}
              </Badge>
            </div>
            {document.description && (
              <p className="text-muted-foreground text-sm mt-1">{document.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleReindex} disabled={reindexing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${reindexing ? 'animate-spin' : ''}`} />
            Re-index
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleCopyId}>
                <Copy className="mr-2 h-4 w-4" /> Copy ID
              </DropdownMenuItem>
              {document.source_url && (
                <DropdownMenuItem onClick={handleCopySourceUrl}>
                  <Link2 className="mr-2 h-4 w-4" /> Copy Source URL
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive"
                onClick={() => setDeleteDialogOpen(true)}
              >
                <Trash2 className="mr-2 h-4 w-4" /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Metadata Grid */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Content Type</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm font-medium capitalize">{document.content_type}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Source</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm font-medium capitalize">{document.source}</p>
            </div>
            {document.source_url && (
              <a
                href={document.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-primary hover:underline flex items-center gap-1 mt-1"
              >
                <ExternalLink className="h-3 w-3" />
                Source URL
              </a>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">File Size</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{formatFileSize(document.file_size)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Chunks</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{document.chunk_count ?? '—'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Embedding Model</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm font-medium">{document.embedding_model || '—'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Created</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm font-medium">{formatDateTime(document.created_at)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Tags */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">Tags</CardTitle>
            <CardDescription>Categorize and organize this document</CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setEditTags(!editTags)}
          >
            <Edit3 className="mr-2 h-4 w-4" />
            {editTags ? 'Cancel' : 'Edit'}
          </Button>
        </CardHeader>
        <CardContent>
          {editTags ? (
            <div className="flex items-center gap-2">
              <Input
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="Enter tags separated by commas"
                className="flex-1"
              />
              <Button size="sm" onClick={handleSaveTags}>
                <Save className="mr-2 h-4 w-4" /> Save
              </Button>
            </div>
          ) : document.tags.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {document.tags.map((tag) => (
                <Badge key={tag} variant="secondary">
                  <Tag className="mr-1 h-3 w-3" />
                  {tag}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No tags</p>
          )}
        </CardContent>
      </Card>

      {/* Content Preview */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Content Preview</CardTitle>
          <CardDescription>
            {document.content
              ? `${document.content.length.toLocaleString()} characters`
              : 'No content preview available'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {document.content ? (
            <div>
              <div className={`prose prose-sm max-w-none dark:prose-invert whitespace-pre-wrap text-sm leading-relaxed ${
                showFullContent ? '' : 'line-clamp-[20]'
              }`}>
                {document.content}
              </div>
              {document.content.length > 1000 && (
                <Button
                  variant="link"
                  size="sm"
                  className="mt-2"
                  onClick={() => setShowFullContent(!showFullContent)}
                >
                  {showFullContent ? 'Show less' : `Show more (${document.content.length.toLocaleString()} total characters)`}
                </Button>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-8 text-center">
              Content not available for preview
            </p>
          )}
        </CardContent>
      </Card>

      {/* In-document Semantic Search */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Search Within Document</CardTitle>
          <CardDescription>Ask a question about this document</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Ask a question about this document..."
                className="pl-9"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSearch();
                }}
              />
            </div>
            <Button onClick={handleSearch} disabled={searching || !searchQuery.trim()}>
              {searching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              Search
            </Button>
          </div>

          {searchResults.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-sm font-medium text-muted-foreground">
                Results
              </p>
              {searchResults.map((result, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs text-muted-foreground line-clamp-3 flex-1">
                      {result.snippet}
                    </p>
                    <Badge variant="secondary" className="flex-shrink-0 text-xs">
                      {(result.score * 100).toFixed(0)}%
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Delete Document</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{document.title}&rdquo;? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
