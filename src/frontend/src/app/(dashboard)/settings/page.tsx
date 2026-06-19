'use client';

import { useState } from 'react';
import {
  Settings,
  User,
  Bell,
  Shield,
  CreditCard,
  Globe,
  Palette,
  Key,
  Users,
  Webhook,
  Save,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import { Input } from '@/components/atoms/input';
import { Label } from '@/components/atoms/label';
import { Separator } from '@/components/atoms/separator';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/molecules/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/molecules/tabs';
import { Switch } from '@/components/atoms/switch';
import { toast } from 'sonner';

export default function SettingsPage() {
  const [saving, setSaving] = useState<Record<string, boolean>>({});

  const handleSave = (section: string) => {
    setSaving((prev) => ({ ...prev, [section]: true }));
    setTimeout(() => {
      setSaving((prev) => ({ ...prev, [section]: false }));
      toast.success(`${section} settings saved`);
    }, 800);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Manage your account, workspace, and application preferences
        </p>
      </div>

      <Tabs defaultValue="profile">
        <TabsList className="grid w-full grid-cols-4 lg:grid-cols-6">
          <TabsTrigger value="profile"><User className="mr-2 h-4 w-4" /> Profile</TabsTrigger>
          <TabsTrigger value="workspace"><Globe className="mr-2 h-4 w-4" /> Workspace</TabsTrigger>
          <TabsTrigger value="notifications"><Bell className="mr-2 h-4 w-4" /> Notifications</TabsTrigger>
          <TabsTrigger value="security"><Shield className="mr-2 h-4 w-4" /> Security</TabsTrigger>
          <TabsTrigger value="billing" className="hidden lg:flex"><CreditCard className="mr-2 h-4 w-4" /> Billing</TabsTrigger>
          <TabsTrigger value="api" className="hidden lg:flex"><Key className="mr-2 h-4 w-4" /> API</TabsTrigger>
        </TabsList>

        {/* Profile */}
        <TabsContent value="profile" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>Update your personal details and public profile</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="displayName">Display Name</Label>
                  <Input id="displayName" defaultValue="John Doe" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" defaultValue="john@example.com" />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="avatar">Avatar URL</Label>
                <Input id="avatar" placeholder="https://example.com/avatar.jpg" />
              </div>
              <Button onClick={() => handleSave('Profile')} disabled={saving.profile}>
                {saving.profile ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</> : <><Save className="mr-2 h-4 w-4" /> Save Changes</>}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Workspace */}
        <TabsContent value="workspace" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Workspace Settings</CardTitle>
              <CardDescription>Configure your workspace name, branding, and localization</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="workspaceName">Workspace Name</Label>
                  <Input id="workspaceName" defaultValue="Default Workspace" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="workspaceSlug">Slug</Label>
                  <Input id="workspaceSlug" defaultValue="default" />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Input id="timezone" defaultValue="America/New_York" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="locale">Locale</Label>
                <Input id="locale" defaultValue="en-US" />
              </div>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg border bg-card w-16 h-16 flex items-center justify-center text-2xl font-bold text-primary">
                  A
                </div>
                <div className="space-y-2 flex-1">
                  <Label htmlFor="brandingLogo">Brand Logo URL</Label>
                  <Input id="brandingLogo" placeholder="https://example.com/logo.png" />
                </div>
              </div>
              <Button onClick={() => handleSave('Workspace')} disabled={saving.workspace}>
                {saving.workspace ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</> : <><Save className="mr-2 h-4 w-4" /> Save Changes</>}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications */}
        <TabsContent value="notifications" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>Choose which notifications you receive</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {[
                { label: 'Email notifications', desc: 'Receive email updates for campaign results and reports' },
                { label: 'Push notifications', desc: 'Browser notifications for real-time alerts' },
                { label: 'Weekly digest', desc: 'Weekly summary of all marketing activities' },
                { label: 'Campaign alerts', desc: 'Alerts when campaigns complete or need attention' },
                { label: 'AI agent notifications', desc: 'When AI agents complete tasks or need review' },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{item.label}</p>
                    <p className="text-sm text-muted-foreground">{item.desc}</p>
                  </div>
                  <Switch defaultChecked={item.label !== 'Weekly digest'} />
                </div>
              ))}
              <Button onClick={() => handleSave('Notifications')} disabled={saving.notifications}>
                {saving.notifications ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</> : <><Save className="mr-2 h-4 w-4" /> Save Changes</>}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security */}
        <TabsContent value="security" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Security Settings</CardTitle>
              <CardDescription>Manage your password and security preferences</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="currentPassword">Current Password</Label>
                <Input id="currentPassword" type="password" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="newPassword">New Password</Label>
                  <Input id="newPassword" type="password" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm Password</Label>
                  <Input id="confirmPassword" type="password" />
                </div>
              </div>
              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium">Two-Factor Authentication</p>
                  <p className="text-sm text-muted-foreground">Add an extra layer of security to your account</p>
                </div>
                <Switch />
              </div>
              <Button onClick={() => handleSave('Security')} disabled={saving.security}>
                {saving.security ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Updating...</> : <><Save className="mr-2 h-4 w-4" /> Update</>}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Billing */}
        <TabsContent value="billing" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Plan & Billing</CardTitle>
              <CardDescription>Manage your subscription and payment methods</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="p-4 rounded-lg border bg-muted/50 mb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold">Pro Plan</p>
                    <p className="text-sm text-muted-foreground">$49/month — billed monthly</p>
                  </div>
                  <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">Active</Badge>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b">
                  <span className="text-sm">Seats used</span>
                  <span className="text-sm font-medium">3 / 10</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b">
                  <span className="text-sm">Contacts</span>
                  <span className="text-sm font-medium">1,247 / 10,000</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b">
                  <span className="text-sm">AI agent calls</span>
                  <span className="text-sm font-medium">847 / 5,000</span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm">Storage used</span>
                  <span className="text-sm font-medium">2.3 GB / 50 GB</span>
                </div>
              </div>
              <Button variant="outline" className="mt-4 w-full">Manage Subscription</Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API */}
        <TabsContent value="api" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle>API Keys</CardTitle>
              <CardDescription>Manage your API keys for integrations</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="p-8 text-center text-muted-foreground">
                <Key className="h-8 w-8 mx-auto mb-3 opacity-50" />
                <p>API key management is available in the full version.</p>
                <Button variant="outline" className="mt-3">Generate API Key</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Badge({ children, className, variant }: { children: React.ReactNode; className?: string; variant?: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${className || ''}`}>
      {children}
    </span>
  );
}
