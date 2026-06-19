'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Upload,
  Search,
  Filter,
  Image,
  Film,
  FileText,
  Music,
  File,
  Trash2,
  Download,
  MoreHorizontal,
  Grid3X3,
  List,
  Loader2,
  X,
  Folder,
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
} from '@/components/molecules/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/molecules/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/molecules/table';
import { Skeleton } from '@/components/atoms/skeleton';
import { formatDate, formatCurrency } from '@/lib/utils';
import { mediaApi } from '@/lib/api/media';
import type { MediaAsset, MediaType } from '@/lib/api/media';
import { toast } from 'sonner';

const mediaTypeIcons: Record<string, React.ElementType> = {
  image: Image,
  video: Film,
  document: FileText,
  audio: Music,
  other: File,
};

const mediaTypeColors: Record<string, string> = {
  image: 'bg-sky-100 text-sky-700 dark:bg-sky-900 dark:text-sky-300',
  video: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  document: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  audio: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300',
  other: 'bg-muted text-muted-foreground',
};

const mediaTypeLabels: Record<string, string> = {
  image: 'Image',
  video: 'Video',
  document: 'Document',
  audio: 'Audio',
  other: 'Other',
};

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function getFileIconUrl(asset: MediaAsset): string | null {
  if (asset.thumbnail_url) return asset.thumbnail_url;
  if (asset.media_type === 'image' && asset.url) return asset.url;
  return null;
}

export default function MediaPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [search, setSearch] = useState('');
  const [mediaTypeFilter, setMediaTypeFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [uploading, setUploading] = useState(false);
  const [selectedAssets, setSelectedAssets] = useState<Set<string>>(new Set());
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fetchAssets = useCallback(async () => {
    try {
      setLoading(true);
      const params: {
        page?: number;
        limit?: number;
        media_type?: MediaType;
        search?: string;
        folder?: string;
      } = { page, limit: 24 };
      if (mediaTypeFilter !== 'all') params.media_type = mediaTypeFilter as MediaType;
      if (search) params.search = search;
      // Note: category is handled via tags/search on backend
      const res = await mediaApi.list(params);
      setAssets(res.data);
      setTotal(res.meta.total);
      setHasMore(res.meta.has_more);
    } catch (err) {
      console.error('Failed to load media:', err);
      toast.error('Failed to load media assets');
    } finally {
      setLoading(false);
    }
  }, [page, search, mediaTypeFilter]);

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    try {
      setUploading(true);
      const uploadPromises = Array.from(files).map((file) =>
        mediaApi.upload({ file })
      );
      const results = await Promise.all(uploadPromises);
      toast.success(`${results.length} file(s) uploaded successfully`);
      fetchAssets();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedAssets((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedAssets.size === assets.length) {
      setSelectedAssets(new Set());
    } else {
      setSelectedAssets(new Set(assets.map((a) => a.id)));
    }
  };

  const handleBatchDelete = async () => {
    try {
      setDeleting(true);
      await Promise.all(
        Array.from(selectedAssets).map((id) => mediaApi.delete(id))
      );
      toast.success(`${selectedAssets.size} asset(s) deleted`);
      setSelectedAssets(new Set());
      setDeleteDialogOpen(false);
      fetchAssets();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete assets');
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteSingle = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await mediaApi.delete(id);
      toast.success('Asset deleted');
      fetchAssets();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete asset');
    }
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Media Library</h1>
          <p className="text-muted-foreground mt-1">
            Upload, manage, and organize your media assets
          </p>
        </div>
        <div className="flex items-center gap-2">
          {selectedAssets.size > 0 && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setDeleteDialogOpen(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete ({selectedAssets.size})
            </Button>
          )}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt"
            className="hidden"
            onChange={handleUpload}
          />
          <Button onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Uploading...</>
            ) : (
              <><Upload className="mr-2 h-4 w-4" /> Upload</>
            )}
          </Button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search media files..."
            className="pl-9"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
          {search && (
            <button
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              onClick={() => { setSearch(''); setPage(1); }}
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <Select
          value={mediaTypeFilter}
          onValueChange={(v) => { setMediaTypeFilter(v); setPage(1); }}
        >
          <SelectTrigger className="w-[150px]">
            <Filter className="mr-2 h-4 w-4" />
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="image">Images</SelectItem>
            <SelectItem value="video">Videos</SelectItem>
            <SelectItem value="document">Documents</SelectItem>
            <SelectItem value="audio">Audio</SelectItem>
            <SelectItem value="other">Other</SelectItem>
          </SelectContent>
        </Select>
        <div className="flex items-center rounded-md border p-1">
          <Button
            variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
            size="icon-sm"
            onClick={() => setViewMode('grid')}
          >
            <Grid3X3 className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'secondary' : 'ghost'}
            size="icon-sm"
            onClick={() => setViewMode('list')}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Grid View */}
      {viewMode === 'grid' && (
        <>
          {loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {Array.from({ length: 12 }).map((_, i) => (
                <Card key={i}>
                  <Skeleton className="aspect-square w-full rounded-t-lg" />
                  <CardContent className="p-3 space-y-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-3 w-2/3" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : assets.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-16">
                <div className="rounded-full bg-muted p-4 mb-4">
                  <Image className="h-10 w-10 text-muted-foreground" />
                </div>
                <p className="text-lg font-medium mb-1">No media assets</p>
                <p className="text-sm text-muted-foreground mb-4">
                  Upload images, videos, documents, and more
                </p>
                <Button onClick={() => fileInputRef.current?.click()}>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Files
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {assets.map((asset) => {
                const TypeIcon = mediaTypeIcons[asset.media_type] || File;
                const previewUrl = getFileIconUrl(asset);
                const isSelected = selectedAssets.has(asset.id);

                return (
                  <Card
                    key={asset.id}
                    className={`cursor-pointer overflow-hidden transition-all hover:ring-2 hover:ring-primary/50 ${
                      isSelected ? 'ring-2 ring-primary' : ''
                    }`}
                    onClick={() => router.push(`/media/${asset.id}`)}
                  >
                    {/* Thumbnail / Icon */}
                    <div
                      className="relative aspect-square bg-muted flex items-center justify-center"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <input
                        type="checkbox"
                        className="absolute top-2 left-2 z-10 h-4 w-4 rounded border-gray-300"
                        checked={isSelected}
                        onChange={() => toggleSelect(asset.id)}
                      />
                      {previewUrl ? (
                        <img
                          src={previewUrl}
                          alt={asset.alt_text || asset.filename}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div
                          className={`rounded-lg p-4 ${
                            mediaTypeColors[asset.media_type] || 'bg-muted'
                          }`}
                        >
                          <TypeIcon className="h-10 w-10" />
                        </div>
                      )}
                      <Badge
                        variant="secondary"
                        className="absolute bottom-2 right-2 text-[10px] px-1.5 py-0"
                      >
                        {formatFileSize(asset.size_bytes)}
                      </Badge>
                    </div>
                    <CardContent className="p-3">
                      <p className="text-xs font-medium truncate" title={asset.filename}>
                        {asset.filename}
                      </p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {formatDate(asset.created_at)}
                      </p>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* List View */}
      {viewMode === 'list' && (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40px]">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-gray-300"
                      checked={assets.length > 0 && selectedAssets.size === assets.length}
                      onChange={toggleSelectAll}
                    />
                  </TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead className="hidden md:table-cell">Type</TableHead>
                  <TableHead className="hidden md:table-cell">Size</TableHead>
                  <TableHead className="hidden lg:table-cell">Created</TableHead>
                  <TableHead className="w-[80px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  Array.from({ length: 8 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell><Skeleton className="h-4 w-4" /></TableCell>
                      <TableCell><Skeleton className="h-5 w-48" /></TableCell>
                      <TableCell className="hidden md:table-cell"><Skeleton className="h-5 w-20" /></TableCell>
                      <TableCell className="hidden md:table-cell"><Skeleton className="h-5 w-16" /></TableCell>
                      <TableCell className="hidden lg:table-cell"><Skeleton className="h-5 w-28" /></TableCell>
                      <TableCell><Skeleton className="h-8 w-16" /></TableCell>
                    </TableRow>
                  ))
                ) : assets.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                      No media assets found
                    </TableCell>
                  </TableRow>
                ) : (
                  assets.map((asset) => {
                    const TypeIcon = mediaTypeIcons[asset.media_type] || File;

                    return (
                      <TableRow
                        key={asset.id}
                        className="cursor-pointer"
                        onClick={() => router.push(`/media/${asset.id}`)}
                      >
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            className="h-4 w-4 rounded border-gray-300"
                            checked={selectedAssets.has(asset.id)}
                            onChange={() => toggleSelect(asset.id)}
                          />
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div
                              className={`rounded-lg p-2 ${
                                mediaTypeColors[asset.media_type] || 'bg-muted'
                              }`}
                            >
                              <TypeIcon className="h-5 w-5" />
                            </div>
                            <div>
                              <p className="font-medium text-sm truncate max-w-[200px]" title={asset.filename}>
                                {asset.filename}
                              </p>
                              {asset.alt_text && (
                                <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                  {asset.alt_text}
                                </p>
                              )}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          <Badge variant="outline" className="text-xs">
                            {mediaTypeLabels[asset.media_type] || asset.media_type}
                          </Badge>
                        </TableCell>
                        <TableCell className="hidden md:table-cell text-sm text-muted-foreground">
                          {formatFileSize(asset.size_bytes)}
                        </TableCell>
                        <TableCell className="hidden lg:table-cell text-sm text-muted-foreground">
                          {formatDate(asset.created_at)}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                              <Button variant="ghost" size="icon-sm">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuLabel>Actions</DropdownMenuLabel>
                              <DropdownMenuItem onClick={() => router.push(`/media/${asset.id}`)}>
                                View Details
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={async (e) => {
                                e.stopPropagation();
                                try {
                                  const res = await mediaApi.getDownloadUrl(asset.id);
                                  window.open(res.data.url, '_blank');
                                } catch {
                                  toast.error('Failed to get download URL');
                                }
                              }}>
                                Download
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-destructive"
                                onClick={(e) => handleDeleteSingle(asset.id, e)}
                              >
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
      )}

      {/* Pagination */}
      {!loading && assets.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {Math.ceil(total / 24)} ({total} total)
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!hasMore}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Batch Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Assets</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {selectedAssets.size} asset(s)?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleBatchDelete} disabled={deleting}>
              {deleting ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Deleting...</>
              ) : (
                <>Delete {selectedAssets.size} Asset(s)</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
