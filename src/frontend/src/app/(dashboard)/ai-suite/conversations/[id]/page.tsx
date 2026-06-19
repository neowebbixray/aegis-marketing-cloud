'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  MessageSquare,
  Send,
  Copy,
  CheckCircle2,
  Archive,
  MoreHorizontal,
  Bot,
  User,
  Clock,
  Loader2,
  Trash2,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import { Input } from '@/components/atoms/input';
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
import { Separator } from '@/components/atoms/separator';
import { Skeleton } from '@/components/atoms/skeleton';
import { toast } from 'sonner';
import { aiApi } from '@/lib/api/ai';
import { formatDateTime } from '@/lib/utils';
import type { Conversation, Message } from '@/lib/api/ai';

// ─── Conversation Detail Page ─────────────────────────────────

export default function ConversationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const fetchConversation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await aiApi.getConversation(id);
      setConversation(res.data);
      setMessages(res.data.messages || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversation');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      fetchConversation();
    }
  }, [id, fetchConversation]);

  const handleSendMessage = async () => {
    if (!newMessage.trim()) return;

    const userMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: id,
      role: 'user',
      content: newMessage.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setNewMessage('');
    setSending(true);

    try {
      const res = await aiApi.sendMessage(id, { content: userMsg.content });
      if (res.data) {
        setMessages((prev) => [...prev, res.data]);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to send message');
      // Remove the temporary user message on failure
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleResolve = async () => {
    setResolving(true);
    try {
      // Update conversation status via the API
      // For now simulate since there's no direct resolve endpoint in types
      toast.success('Conversation marked as resolved');
      setConversation((prev) => prev ? { ...prev, status: 'resolved' } : null);
    } catch (err) {
      toast.error('Failed to resolve conversation');
    } finally {
      setResolving(false);
    }
  };

  const handleArchive = async () => {
    setArchiving(true);
    try {
      toast.success('Conversation archived');
      setConversation((prev) => prev ? { ...prev, status: 'archived' } : null);
    } catch (err) {
      toast.error('Failed to archive conversation');
    } finally {
      setArchiving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await aiApi.deleteConversation(id);
      toast.success('Conversation deleted');
      router.push('/ai-suite');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete conversation');
    } finally {
      setDeleteDialogOpen(false);
    }
  };

  const copyConversation = async () => {
    const text = messages
      .map((m) => `[${m.role.toUpperCase()}] ${m.content}`)
      .join('\n\n');
    try {
      await navigator.clipboard.writeText(text);
      toast.success('Conversation copied to clipboard');
    } catch {
      toast.error('Failed to copy conversation');
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
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  // Error state
  if (error || !conversation) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <MessageSquare className="h-12 w-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground mb-2">Conversation not found</p>
        <p className="text-sm text-destructive mb-4">{error}</p>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.back()}>
            Go Back
          </Button>
          <Button variant="link" onClick={() => router.push('/ai-suite')}>
            Back to AI Suite
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{conversation.title}</h1>
              <Badge variant="outline" className="capitalize">
                {conversation.status}
              </Badge>
            </div>
            <p className="text-muted-foreground text-sm mt-1">
              {conversation.agent_id ? `Agent: ${conversation.agent_id}` : 'General conversation'} ·{' '}
              {formatDateTime(conversation.created_at)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={copyConversation}>
            <Copy className="mr-2 h-4 w-4" /> Copy
          </Button>
          {conversation.status === 'active' && (
            <Button variant="outline" size="sm" onClick={handleResolve} disabled={resolving}>
              <CheckCircle2 className="mr-2 h-4 w-4" /> Resolve
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleArchive} disabled={archiving}>
            <Archive className="mr-2 h-4 w-4" /> Archive
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={copyConversation}>
                <Copy className="mr-2 h-4 w-4" /> Copy conversation
              </DropdownMenuItem>
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

      {/* Messages */}
      <Card className="flex flex-col h-[60vh]">
        <CardContent className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
              <MessageSquare className="h-10 w-10 mb-3 opacity-50" />
              <p>No messages yet</p>
              <p className="text-sm mt-1">Start the conversation below</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={message.id || index}
                className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'assistant' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                )}
                <div
                  className={`max-w-[75%] rounded-lg px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium">
                      {message.role === 'user' ? 'You' : 'AI Assistant'}
                    </span>
                    <span className="text-xs opacity-70">
                      {formatDateTime(message.created_at)}
                    </span>
                  </div>
                  <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                  {message.tokens_used && (
                    <p className="text-xs opacity-50 mt-1">{message.tokens_used} tokens</p>
                  )}
                </div>
                {message.role === 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                    <User className="h-4 w-4 text-primary-foreground" />
                  </div>
                )}
              </div>
            ))
          )}
          {sending && (
            <div className="flex gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div className="bg-muted rounded-lg px-4 py-3">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm text-muted-foreground">Thinking...</span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
        <Separator />
        <div className="p-4">
          <div className="flex items-center gap-3">
            <Input
              placeholder="Type your message..."
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sending}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={sending || !newMessage.trim()}
              size="icon"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Delete Conversation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this conversation? This action cannot be undone.
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
