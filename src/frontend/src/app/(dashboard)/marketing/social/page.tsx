'use client';

import { Share2, Users, MessageSquare, TrendingUp, Image, Calendar } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/molecules/card';
import { Button } from '@/components/atoms/button';

export default function SocialPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-pink-500/10">
            <Share2 className="h-6 w-6 text-pink-500" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Social</h1>
            <p className="text-muted-foreground mt-1">Social media management and analytics</p>
          </div>
        </div>
        <Button disabled>Connect Account</Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Connected Accounts</CardTitle>
            <Share2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent><div className="text-2xl font-bold">0</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Scheduled Posts</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent><div className="text-2xl font-bold">—</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Engagement Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent><div className="text-2xl font-bold">—</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Followers</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent><div className="text-2xl font-bold">—</div></CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-12 text-center text-muted-foreground">
          <Share2 className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium mb-2">Social Media Module Coming Soon</p>
          <p className="text-sm mb-6">Connect your social accounts to schedule posts, track engagement, and manage your brand presence across platforms.</p>
          <Button variant="outline">Learn More</Button>
        </CardContent>
      </Card>
    </div>
  );
}
