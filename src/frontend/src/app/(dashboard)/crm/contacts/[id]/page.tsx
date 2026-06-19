'use client';

import { useParams, useRouter } from 'next/navigation';
import { useContact, useContactActivities } from '@/hooks/use-contacts';
import {
  ArrowLeft,
  Mail,
  Phone,
  Building2,
  MapPin,
  Calendar,
  Edit,
  MoreHorizontal,
  MessageSquare,
  PhoneCall,
  MailCheck,
  CalendarDays,
  Activity as ActivityIcon,
  FileText,
  Link2,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/atoms/avatar';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/molecules/card';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/molecules/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/molecules/dropdown-menu';
import { Separator } from '@/components/atoms/separator';
import { Skeleton } from '@/components/atoms/skeleton';
import { formatDate, formatDateTime, getInitials } from '@/lib/utils';
import type { Activity, ActivityType } from '@/types';

// ─── Activity Icon ────────────────────────────────────────

function getActivityIcon(type: ActivityType) {
  switch (type) {
    case 'note': return MessageSquare;
    case 'call': return PhoneCall;
    case 'email': return MailCheck;
    case 'meeting': return CalendarDays;
    case 'task': return ActivityIcon;
    default: return ActivityIcon;
  }
}

function getActivityColor(type: ActivityType) {
  switch (type) {
    case 'note': return 'bg-warning-100 text-warning-700 dark:bg-warning-900 dark:text-warning-300';
    case 'call': return 'bg-success-100 text-success-700 dark:bg-success-900 dark:text-success-300';
    case 'email': return 'bg-info-100 text-info-700 dark:bg-info-900 dark:text-info-300';
    case 'meeting': return 'bg-accent-100 text-accent-700 dark:bg-accent-900 dark:text-accent-300';
    case 'task': return 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300';
    default: return 'bg-muted text-muted-foreground';
  }
}

// ─── Info Row ─────────────────────────────────────────────

function InfoRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string | undefined | null }) {
  return (
    <div className="flex items-center gap-3">
      <div className="rounded-lg bg-muted p-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-medium">{value || '—'}</p>
      </div>
    </div>
  );
}

const stageColors: Record<string, string> = {
  lead: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-100',
  qualified: 'bg-info-100 text-info-800 dark:bg-info-900 dark:text-info-100',
  opportunity: 'bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-100',
  customer: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100',
  churned: 'bg-destructive/10 text-destructive',
  inactive: 'bg-muted text-muted-foreground',
};

// ─── Contact Detail Page ──────────────────────────────────

export default function ContactDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;
  const { data: contactData, isLoading, error } = useContact(id);
  const { data: activitiesData } = useContactActivities(id);

  const contact = contactData?.data;
  const activities = activitiesData?.data ?? [];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32 mt-2" />
          </div>
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !contact) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <p className="text-muted-foreground">Contact not found</p>
        <Button variant="link" onClick={() => router.push('/crm/contacts')}>
          Back to contacts
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button + header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <Avatar className="h-14 w-14">
            <AvatarImage src={contact.avatar_url} />
            <AvatarFallback className="text-lg">
              {getInitials(`${contact.first_name} ${contact.last_name}`)}
            </AvatarFallback>
          </Avatar>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">
                {contact.first_name} {contact.last_name}
              </h1>
              <Badge variant="outline" className={stageColors[contact.lifecycle_stage]}>
                {contact.lifecycle_stage.charAt(0).toUpperCase() + contact.lifecycle_stage.slice(1)}
              </Badge>
            </div>
            <p className="text-muted-foreground">
              {contact.job_title ? `${contact.job_title} at ` : ''}
              {contact.company || 'No company'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuItem>Merge Contact</DropdownMenuItem>
              <DropdownMenuItem>Export</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive">Delete Contact</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Content tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="deals">Deals</TabsTrigger>
          <TabsTrigger value="activities">Activities</TabsTrigger>
          <TabsTrigger value="notes">Notes</TabsTrigger>
          <TabsTrigger value="files">Files</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Contact Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Contact Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <InfoRow icon={Mail} label="Email" value={contact.email} />
                <InfoRow icon={Phone} label="Phone" value={contact.phone} />
                <InfoRow icon={Building2} label="Company" value={contact.company} />
                <InfoRow icon={MapPin} label="Job Title" value={contact.job_title} />
                <InfoRow icon={Calendar} label="Created" value={formatDate(contact.created_at)} />
              </CardContent>
            </Card>

            {/* Details */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Source</span>
                  <Badge variant="outline">
                    {contact.source.charAt(0).toUpperCase() + contact.source.slice(1)}
                  </Badge>
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Owner</span>
                  <span className="text-sm font-medium">
                    {contact.owner?.display_name || 'Unassigned'}
                  </span>
                </div>
                <Separator />
                <div>
                  <span className="text-sm text-muted-foreground">Tags</span>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {contact.tags.length > 0
                      ? contact.tags.map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))
                      : <span className="text-sm text-muted-foreground">No tags</span>}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Deals Tab */}
        <TabsContent value="deals">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Deals</CardTitle>
              <CardDescription>Associated deals and opportunities</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground py-8 text-center">
                No deals associated with this contact yet.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Activities Tab */}
        <TabsContent value="activities">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Activity Timeline</CardTitle>
              <CardDescription>All interactions with this contact</CardDescription>
            </CardHeader>
            <CardContent>
              {activities.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  No activities recorded yet.
                </p>
              ) : (
                <div className="space-y-0">
                  {activities.map((activity: Activity, index: number) => {
                    const Icon = getActivityIcon(activity.type);
                    return (
                      <div key={activity.id} className="flex gap-4 py-3">
                        <div className="flex flex-col items-center">
                          <div className={`rounded-full border p-2 ${getActivityColor(activity.type)}`}>
                            <Icon className="h-4 w-4" />
                          </div>
                          {index < activities.length - 1 && (
                            <div className="w-px flex-1 bg-border mt-2" />
                          )}
                        </div>
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-medium">{activity.title}</p>
                            <span className="text-xs text-muted-foreground">
                              {formatDateTime(activity.created_at)}
                            </span>
                          </div>
                          {activity.description && (
                            <p className="text-sm text-muted-foreground">{activity.description}</p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notes Tab */}
        <TabsContent value="notes">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Notes</CardTitle>
              <CardDescription>Internal notes about this contact</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground py-8 text-center">
                {contact.notes || 'No notes added yet.'}
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Files Tab */}
        <TabsContent value="files">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Files</CardTitle>
              <CardDescription>Attachments and documents</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground py-8 text-center">
                No files attached yet.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
