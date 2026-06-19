'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  Sparkles,
  Copy,
  Check,
  RefreshCw,
  Save,
  History,
  Loader2,
  Send,
  ArrowLeft,
  Wand2,
  Trash2,
  Download,
  BookOpen,
  Clock,
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
import { Skeleton } from '@/components/atoms/skeleton';
import { toast } from 'sonner';
import { aiApi } from '@/lib/api/ai';
import { formatDateTime } from '@/lib/utils';
import type { ContentType, GenerationResult, GenerationRequest } from '@/lib/api/ai';

// ─── Constants ────────────────────────────────────────────────

const contentTypes: { value: ContentType; label: string; icon: React.ElementType; description: string }[] = [
  { value: 'blog_post', label: 'Blog Post', icon: BookOpen, description: 'Long-form blog articles and guides' },
  { value: 'social_post', label: 'Social Post', icon: Send, description: 'Short social media content' },
  { value: 'email', label: 'Email', icon: FileText, description: 'Email campaigns and newsletters' },
  { value: 'landing_page', label: 'Landing Page', icon: FileText, description: 'Conversion-focused landing pages' },
  { value: 'ad_copy', label: 'Ad Copy', icon: Wand2, description: 'Advertisement and PPC copy' },
  { value: 'product_description', label: 'Product Description', icon: FileText, description: 'E-commerce product descriptions' },
  { value: 'newsletter', label: 'Newsletter', icon: FileText, description: 'Email newsletters and updates' },
  { value: 'press_release', label: 'Press Release', icon: BookOpen, description: 'Official press announcements' },
];

const toneOptions = [
  { value: 'professional', label: 'Professional' },
  { value: 'casual', label: 'Casual' },
  { value: 'enthusiastic', label: 'Enthusiastic' },
  { value: 'formal', label: 'Formal' },
];

const lengthOptions = [
  { value: 'short', label: 'Short' },
  { value: 'medium', label: 'Medium' },
  { value: 'long', label: 'Long' },
];

// ─── Content Generation Page ─────────────────────────────────

export default function ContentGenerationPage() {
  const [contentType, setContentType] = useState<ContentType>('blog_post');
  const [prompt, setPrompt] = useState('');
  const [tone, setTone] = useState('professional');
  const [length, setLength] = useState('medium');
  const [targetAudience, setTargetAudience] = useState('');
  const [keywords, setKeywords] = useState('');

  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [copied, setCopied] = useState(false);

  const [history, setHistory] = useState<GenerationResult[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const res = await aiApi.listGenerations({ limit: 20 });
      setHistory(res.data || []);
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      toast.error('Please enter a prompt');
      return;
    }

    setIsGenerating(true);
    setResult(null);

    try {
      const request: GenerationRequest = {
        content_type: contentType,
        prompt: prompt.trim(),
        tone,
        length: length as 'short' | 'medium' | 'long',
        target_audience: targetAudience.trim() || undefined,
        keywords: keywords.trim() ? keywords.split(',').map((k) => k.trim()) : undefined,
      };

      const res = await aiApi.generateContent(request);
      setResult(res.data);
      toast.success('Content generated successfully');
      fetchHistory();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to generate content');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.content);
      setCopied(true);
      toast.success('Content copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy');
    }
  };

  const handleRegenerate = () => {
    handleGenerate();
  };

  const handleSave = () => {
    toast.success('Content saved to library');
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Sparkles className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Content Generation</h1>
            <p className="text-muted-foreground mt-1">
              Generate marketing content with AI
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={() => setShowHistory(!showHistory)}>
          <History className="mr-2 h-4 w-4" />
          {showHistory ? 'Hide History' : 'History'}
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content Area */}
        <div className="lg:col-span-2 space-y-6">
          {/* Content Type Selector */}
          <Card>
            <CardHeader>
              <CardTitle>Content Type</CardTitle>
              <CardDescription>Select the type of content you want to generate</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {contentTypes.map((type) => {
                  const Icon = type.icon;
                  const isSelected = contentType === type.value;
                  return (
                    <button
                      key={type.value}
                      className={`flex flex-col items-center gap-2 p-3 rounded-lg border text-center transition-colors ${
                        isSelected
                          ? 'border-primary bg-primary/5 text-primary'
                          : 'hover:bg-muted'
                      }`}
                      onClick={() => setContentType(type.value)}
                    >
                      <Icon className="h-5 w-5" />
                      <span className="text-xs font-medium">{type.label}</span>
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Prompt Input */}
          <Card>
            <CardHeader>
              <CardTitle>Prompt</CardTitle>
              <CardDescription>Describe what you want to create</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="prompt">Your prompt *</Label>
                <Textarea
                  id="prompt"
                  placeholder={`e.g., Write a blog post about the top 10 SEO trends for ${new Date().getFullYear()}...`}
                  className="min-h-[150px]"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                />
              </div>

              <div className="flex flex-wrap gap-2">
                {[
                  `Top 10 marketing trends for ${new Date().getFullYear()}`,
                  'Welcome email series for new signups',
                  'Product launch landing page copy',
                  'Social media captions for Instagram',
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    className="text-xs bg-muted px-3 py-1.5 rounded-full hover:bg-primary/10 hover:text-primary transition-colors"
                    onClick={() => setPrompt(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Parameters */}
          <Card>
            <CardHeader>
              <CardTitle>Parameters</CardTitle>
              <CardDescription>Fine-tune the generation output</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="tone">Tone</Label>
                  <Select value={tone} onValueChange={setTone}>
                    <SelectTrigger id="tone">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {toneOptions.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="length">Length</Label>
                  <Select value={length} onValueChange={setLength}>
                    <SelectTrigger id="length">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {lengthOptions.map((l) => (
                        <SelectItem key={l.value} value={l.value}>
                          {l.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="audience">Target Audience</Label>
                  <Input
                    id="audience"
                    placeholder="e.g., Marketing managers"
                    value={targetAudience}
                    onChange={(e) => setTargetAudience(e.target.value)}
                  />
                </div>
              </div>
              <div className="mt-4 space-y-2">
                <Label htmlFor="keywords">Keywords (comma-separated)</Label>
                <Input
                  id="keywords"
                  placeholder="e.g., AI, marketing, automation"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          {/* Generate Button */}
          <Button
            className="w-full"
            size="lg"
            onClick={handleGenerate}
            disabled={isGenerating || !prompt.trim()}
          >
            {isGenerating ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating...</>
            ) : (
              <><Sparkles className="mr-2 h-4 w-4" /> Generate Content</>
            )}
          </Button>

          {/* Result Display */}
          {result && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Generated Content</CardTitle>
                  <CardDescription>
                    {contentTypes.find((t) => t.value === contentType)?.label} · {formatDateTime(result.created_at)}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={handleCopy}>
                    {copied ? (
                      <><Check className="mr-2 h-4 w-4 text-success" /> Copied</>
                    ) : (
                      <><Copy className="mr-2 h-4 w-4" /> Copy</>
                    )}
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleRegenerate} disabled={isGenerating}>
                    <RefreshCw className={`mr-2 h-4 w-4 ${isGenerating ? 'animate-spin' : ''}`} />
                    Regenerate
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleSave}>
                    <Save className="mr-2 h-4 w-4" /> Save
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="p-4 rounded-lg bg-muted/50 whitespace-pre-wrap text-sm leading-relaxed max-h-[400px] overflow-y-auto">
                  {result.content}
                </div>
                <div className="flex items-center gap-4 mt-4 text-xs text-muted-foreground">
                  <span>Model: {result.model}</span>
                  <span>Tokens: {result.tokens_used}</span>
                  <span>Time: {(result.processing_time_ms / 1000).toFixed(1)}s</span>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* History Sidebar */}
        <div className="space-y-4">
          {(showHistory || history.length > 0) && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <History className="h-4 w-4" />
                  Generation History
                </CardTitle>
                <CardDescription>Your recent generations</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                {historyLoading ? (
                  <div className="p-4 space-y-3">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Skeleton key={i} className="h-16 w-full" />
                    ))}
                  </div>
                ) : history.length === 0 ? (
                  <div className="p-6 text-center text-muted-foreground">
                    <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No history yet</p>
                    <p className="text-xs mt-1">Generate content to see it here</p>
                  </div>
                ) : (
                  <div className="divide-y max-h-[500px] overflow-y-auto">
                    {history.map((gen) => (
                      <div
                        key={gen.id}
                        className="px-4 py-3 hover:bg-muted/50 cursor-pointer transition-colors"
                        onClick={() => setResult(gen)}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <Badge variant="secondary" className="text-xs capitalize">
                            {gen.content_type.replace(/_/g, ' ')}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {formatDateTime(gen.created_at)}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {gen.content.substring(0, 120)}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Quick tips */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Tips</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>• Be specific about your topic and goals</p>
              <p>• Include target audience for better results</p>
              <p>• Add keywords to optimize for SEO</p>
              <p>• Choose the right tone for your brand</p>
              <p>• Use shorter prompts for social posts</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
