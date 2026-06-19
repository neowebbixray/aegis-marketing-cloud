'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Download,
  Trash2,
  Copy,
  Image,
  Film,
  FileText,
  Music,
  File,
  Calendar,
  HardDrive,
  Maximize2,
  Edit,
  Check,
  X,
  Loader2,
  ExternalLink,
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/molecules/dialog';
import { Skeleton } from '@/components/atoms/skeleton';
import { formatDate, formatDateTime } from '@/lib/utils';
import { mediaApi } from '@/lib/api/media';
import type { MediaAsset } from '@/lib/api/media';
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

function getDimensionsLabel(asset: MediaAsset): string | null {
  if (asset.width && asset.height) {
    return `${asset.width} × ${asset.height} px`;
  }
  return null;
}

export default function MediaDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [asset, setAsset] = useState<MediaAsset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [editingAlt, setEditingAlt] = useState(false);
  const [altText, setAltText] = useState('');
  const [savingAlt, setSavingAlt] = useState(false);

  useEffect(() => {
    const fetchAsset = async () => {
      try {
        setLoading(true);
        const res = await mediaApi.get(id);
        setAsset(res.data);
        setAltText(res.data.alt_text || '');
      } catch (err) {
        setError('Failed to load asset');
        console.error('Failed to load media asset:', err);
      } finally {
        setLoading(false);
      }
    };
    if (id) fetchAsset();
  }, [id]);

  const handleDelete = async () => {
    try {
      setDeleting(true);
      await mediaApi.delete(id);
      toast.success('Asset deleted');
      router.push('/media');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete asset');
    } finally {
      setDeleting(false);
    }
  };

  const handleSaveAltText = async () => {
    try {
      setSavingAlt(true);
      const res = await mediaApi.update(id, { alt_text: altText });
      setAsset(res.data);
      setEditingAlt(false);
      toast.success('Alt text updated');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update alt text');
    } finally {
      setSavingAlt(false);
    }
  };

  const handleCopyUrl = async () => {
    if (!asset) return;
    try {
      await navigator.clipboard.writeText(asset.url);
      toast.success('URL copied to clipboard');
    } catch {
      toast.error('Failed to copy URL');
    }
  };

  const handleDownload = async () => {
    if (!asset) return;
    try {
      const res = await mediaApi.getDownloadUrl(asset.id);
      window.open(res.data.url, '_blank');
      toast.success('Download started');
    } catch (err) {
      toast.error('Failed to get download URL');
    }
  };

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
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Skeleton className="aspect-video w-full rounded-lg" />
          </div>
          <div>
            <Skeleton className="h-64 w-full rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !asset) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <div className="rounded-full bg-muted p-4 mb-4">
          <File className="h-10 w-10 text-muted-foreground" />
        </div>
        <p className="text-lg font-medium mb-1">Asset not found</p>
        <p className="text-sm text-muted-foreground mb-4">
          The media asset you&apos;re looking for doesn&apos;t exist or has been deleted.
        </p>
        <Button variant="link" onClick={() => router.push('/media')}>
          Back to media library
        </Button>
      </div>
    );
  }

  const TypeIcon = mediaTypeIcons[asset.media_type] || File;
  const previewUrl = asset.thumbnail_url || (asset.media_type === 'image' ? asset.url : null);
  const dimensions = getDimensionsLabel(asset);
  const duration = asset.duration_seconds
    ? `${Math.floor(asset.duration_seconds / 60)}:${String(Math.floor(asset.duration_seconds % 60)).padStart(2, '0')}`
    : null;

  return (
    <div className="space-y-6">
      {/* Back button + header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-3">
            <div className={`rounded-lg p-2 ${mediaTypeColors[asset.media_type] || 'bg-muted'}`}>
              <TypeIcon className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold truncate max-w-md" title={asset.filename}>
                {asset.filename}
              </h1>
              <p className="text-sm text-muted-foreground">
                {mediaTypeLabels[asset.media_type] || asset.media_type} &middot;{' '}
                {formatFileSize(asset.size_bytes)}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleCopyUrl}>
            <Copy className="mr-2 h-4 w-4" />
            Copy URL
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownload}>
            <Download className="mr-2 h-4 w-4" />
            Download
          </Button>
          <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setDeleteDialogOpen(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete Asset</DialogTitle>
                <DialogDescription>
                  Are you sure you want to delete &ldquo;{asset.filename}&rdquo;?
                  This action cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={deleting}
                >
                  {deleting ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Deleting...</>
                  ) : (
                    'Delete Asset'
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Preview */}
        <div className="lg:col-span-2">
          <Card className="overflow-hidden">
            <div className="relative bg-muted flex items-center justify-center min-h-[300px] max-h-[500px]">
              {previewUrl ? (
                <img
                  src={previewUrl}
                  alt={asset.alt_text || asset.filename}
                  className="max-h-[500px] w-full object-contain"
                />
              ) : (
                <div className={`rounded-2xl p-12 ${mediaTypeColors[asset.media_type] || 'bg-muted'}`}>
                  <TypeIcon className="h-24 w-24" />
                </div>
              )}
            </div>
          </Card>

          {/* Alt text editing */}
          <Card className="mt-4">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-lg">Alt Text</CardTitle>
              {!editingAlt && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditingAlt(true)}
                >
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {editingAlt ? (
                <div className="space-y-3">
                  <Input
                    value={altText}
                    onChange={(e) => setAltText(e.target.value)}
                    placeholder="Describe this image for accessibility..."
                  />
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      onClick={handleSaveAltText}
                      disabled={savingAlt}
                    >
                      {savingAlt ? (
                        <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</>
                      ) : (
                        <><Check className="mr-2 h-4 w-4" /> Save</>
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEditingAlt(false);
                        setAltText(asset.alt_text || '');
                      }}
                    >
                      <X className="mr-2 h-4 w-4" />
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {asset.alt_text || 'No alt text set. Click edit to add a description for accessibility.'}
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Metadata sidebar */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Filename</p>
                <p className="text-sm font-medium break-all">{asset.filename}</p>
              </div>
              <Separator />
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Original Filename</p>
                <p className="text-sm font-medium break-all">{asset.original_filename}</p>
              </div>
              <Separator />
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Type</p>
                <Badge variant="outline" className="mt-1">
                  {mediaTypeLabels[asset.media_type] || asset.media_type}
                </Badge>
              </div>
              <Separator />
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">MIME Type</p>
                <p className="text-sm font-medium">{asset.mime_type}</p>
              </div>
              <Separator />
              <div className="flex items-center gap-2">
                <HardDrive className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Size</p>
                  <p className="text-sm font-medium">{formatFileSize(asset.size_bytes)}</p>
                </div>
              </div>
              {dimensions && (
                <>
                  <Separator />
                  <div className="flex items-center gap-2">
                    <Maximize2 className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-xs text-muted-foreground uppercase tracking-wide">Dimensions</p>
                      <p className="text-sm font-medium">{dimensions}</p>
                    </div>
                  </div>
                </>
              )}
              {duration && (
                <>
                  <Separator />
                  <div className="flex items-center gap-2">
                    <Film className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-xs text-muted-foreground uppercase tracking-wide">Duration</p>
                      <p className="text-sm font-medium">{duration}</p>
                    </div>
                  </div>
                </>
              )}
              <Separator />
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Uploaded</p>
                  <p className="text-sm font-medium">{formatDateTime(asset.created_at)}</p>
                </div>
              </div>
              <Separator />
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Status</p>
                <Badge
                  variant={
                    asset.status === 'ready'
                      ? 'success'
                      : asset.status === 'failed'
                        ? 'destructive'
                        : 'warning'
                  }
                  className="mt-1 capitalize"
                >
                  {asset.status}
                </Badge>
              </div>
              {asset.tags.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">Tags</p>
                    <div className="flex flex-wrap gap-1">
                      {asset.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Quick actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full justify-start" onClick={handleDownload}>
                <Download className="mr-2 h-4 w-4" />
                Download File
              </Button>
              <Button variant="outline" className="w-full justify-start" onClick={handleCopyUrl}>
                <Copy className="mr-2 h-4 w-4" />
                Copy URL
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => window.open(asset.url, '_blank')}
              >
                <ExternalLink className="mr-2 h-4 w-4" />
                Open in Browser
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
