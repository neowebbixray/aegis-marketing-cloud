'use client';

import { useState } from 'react';
import {
  Brain,
  Sparkles,
  MessageSquare,
  FileText,
  BarChart3,
  Target,
  PenLine,
  Search,
  Wand2,
  ArrowRight,
  Loader2,
  Zap,
  Shield,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
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
import { Input } from '@/components/atoms/input';
import { Label } from '@/components/atoms/label';
import { Textarea } from '@/components/atoms/textarea';
import { Separator } from '@/components/atoms/separator';
import { Skeleton } from '@/components/atoms/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/molecules/tabs';
import { toast } from 'sonner';

interface AIAgent {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  color: string;
  isAvailable: boolean;
}

const agents: AIAgent[] = [
  { id: 'content-writer', name: 'Content Writer', description: 'Generate blog posts, emails, landing pages, and ad copy', icon: PenLine, color: 'bg-blue-500', isAvailable: true },
  { id: 'campaign-optimizer', name: 'Campaign Optimizer', description: 'Analyze and optimize campaign performance', icon: Target, color: 'bg-green-500', isAvailable: true },
  { id: 'seo-analyst', name: 'SEO Analyst', description: 'Keyword research, content gap analysis, ranking tracking', icon: Search, color: 'bg-purple-500', isAvailable: true },
  { id: 'audience-insights', name: 'Audience Insights', description: 'Segment analysis, behavior prediction, lookalike audiences', icon: BarChart3, color: 'bg-orange-500', isAvailable: true },
  { id: 'email-assistant', name: 'Email Assistant', description: 'Write and A/B test email campaigns', icon: MessageSquare, color: 'bg-pink-500', isAvailable: false },
  { id: 'content-enhancer', name: 'Content Enhancer', description: 'Rewrite, expand, or summarize existing content', icon: Wand2, color: 'bg-teal-500', isAvailable: false },
];

export default function AiSuitePage() {
  const [promptOpen, setPromptOpen] = useState(false);
  const [promptText, setPromptText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async () => {
    if (!promptText.trim()) return;
    setIsGenerating(true);
    // Simulate AI generation
    await new Promise((r) => setTimeout(r, 2000));
    toast.success('AI content generated successfully');
    setIsGenerating(false);
    setPromptOpen(false);
    setPromptText('');
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Brain className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">AI Suite</h1>
            <p className="text-muted-foreground mt-1">
              AI-powered marketing agents to automate and optimize your workflows
            </p>
          </div>
        </div>
        <Dialog open={promptOpen} onOpenChange={setPromptOpen}>
          <DialogTrigger asChild>
            <Button>
              <Sparkles className="mr-2 h-4 w-4" />
              AI Assistant
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>AI Assistant</DialogTitle>
              <DialogDescription>
                Describe what you want to create or optimize — AI agents will handle the rest
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <Label htmlFor="prompt">Your request</Label>
              <Textarea
                id="prompt"
                placeholder="e.g., Write a welcome email series for new SaaS signups..."
                className="mt-2 min-h-[150px]"
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
              />
              <div className="mt-3 flex flex-wrap gap-2">
                {['Write a blog post about SEO trends', 'Create a landing page for product launch', 'Analyze Q2 campaign performance', 'Generate social media captions'].map((suggestion) => (
                  <button
                    key={suggestion}
                    className="text-xs bg-muted px-3 py-1.5 rounded-full hover:bg-primary/10 hover:text-primary transition-colors"
                    onClick={() => setPromptText(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setPromptOpen(false)}>Cancel</Button>
              <Button onClick={handleGenerate} disabled={isGenerating || !promptText.trim()}>
                {isGenerating ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating...</>
                ) : (
                  <><Sparkles className="mr-2 h-4 w-4" /> Generate</>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Available Agents</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{agents.filter((a) => a.isAvailable).length}/{agents.length}</div>
            <p className="text-xs text-muted-foreground">{agents.filter((a) => !a.isAvailable).length} coming soon</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tasks Completed</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,247</div>
            <p className="text-xs text-muted-foreground">+12% this week</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Response</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1.2s</div>
            <p className="text-xs text-muted-foreground">P95: 2.8s</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Guardrails Active</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground">0 blocks today</p>
          </CardContent>
        </Card>
      </div>

      {/* Agent Grid */}
      <div>
        <h2 className="text-xl font-semibold mb-4">AI Agents</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => {
            const Icon = agent.icon;
            return (
              <Card key={agent.id} className={`relative ${!agent.isAvailable ? 'opacity-60' : 'hover:shadow-md transition-shadow'}`}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className={`p-2 rounded-lg ${agent.color} text-white`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    {!agent.isAvailable && (
                      <Badge variant="secondary" className="text-xs">Coming Soon</Badge>
                    )}
                  </div>
                  <CardTitle className="mt-3 text-lg">{agent.name}</CardTitle>
                  <CardDescription>{agent.description}</CardDescription>
                </CardHeader>
                <CardFooter className="border-t pt-4">
                  <Button
                    variant={agent.isAvailable ? 'default' : 'outline'}
                    className="w-full"
                    disabled={!agent.isAvailable}
                    onClick={() => {
                      if (agent.isAvailable) {
                        setPromptOpen(true);
                        toast.info(`Opening ${agent.name}...`);
                      }
                    }}
                  >
                    {agent.isAvailable ? (
                      <><Sparkles className="mr-2 h-4 w-4" /> Use Agent</>
                    ) : (
                      'Coming Soon'
                    )}
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Your latest AI-generated content and analyses</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[
              { action: 'Generated blog post', title: '10 SEO Trends for 2026', time: '2 hours ago', agent: 'Content Writer' },
              { action: 'Optimized campaign', title: 'Q2 Newsletter — Subject Line A/B Test', time: '5 hours ago', agent: 'Campaign Optimizer' },
              { action: 'Keyword research', title: 'Marketing Automation — Top 50 Keywords', time: '1 day ago', agent: 'SEO Analyst' },
            ].map((item, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <p className="text-sm font-medium">{item.action}</p>
                  <p className="text-sm text-muted-foreground">{item.title}</p>
                </div>
                <div className="text-right text-xs text-muted-foreground">
                  <p>{item.time}</p>
                  <p className="text-primary">{item.agent}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
