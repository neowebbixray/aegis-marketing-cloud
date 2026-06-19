'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  CheckCircle2,
  Loader2,
  CreditCard,
  Zap,
  Star,
  Building2,
  ChevronRight,
  Check,
  X,
  Trash2,
  Plus,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import { Separator } from '@/components/atoms/separator';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/molecules/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/molecules/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/molecules/dialog';
import { Skeleton } from '@/components/atoms/skeleton';
import { formatDate, formatCurrency } from '@/lib/utils';
import { billingApi } from '@/lib/api/billing';
import type { Subscription, SubscriptionPlan, PaymentMethod } from '@/lib/api/billing';
import { toast } from 'sonner';

const statusBadgeVariant: Record<string, 'success' | 'warning' | 'destructive' | 'outline' | 'info'> = {
  active: 'success',
  trialing: 'info',
  past_due: 'warning',
  canceled: 'destructive',
  incomplete: 'outline',
};

const planIcons: Record<string, React.ElementType> = {
  free: Zap,
  starter: Zap,
  professional: Star,
  enterprise: Building2,
};

interface PlanCardProps {
  plan: SubscriptionPlan;
  isCurrent: boolean;
  onSelect: (plan: SubscriptionPlan) => void;
}

function PlanCard({ plan, isCurrent, onSelect }: PlanCardProps) {
  const Icon = planIcons[plan.slug] || Zap;
  return (
    <Card className={`relative ${isCurrent ? 'ring-2 ring-primary' : ''}`}>
      {isCurrent && (
        <div className="absolute -top-2.5 left-1/2 -translate-x-1/2">
          <Badge variant="default" className="whitespace-nowrap">Current Plan</Badge>
        </div>
      )}
      <CardHeader className="text-center pt-6">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <Icon className="h-6 w-6 text-primary" />
        </div>
        <CardTitle className="text-xl">{plan.name}</CardTitle>
        <CardDescription>{plan.description}</CardDescription>
      </CardHeader>
      <CardContent className="text-center">
        <div className="mb-4">
          <span className="text-3xl font-bold">
            {formatCurrency(plan.price_monthly)}
          </span>
          <span className="text-muted-foreground">/month</span>
        </div>
        {plan.price_yearly > 0 && (
          <p className="text-sm text-muted-foreground mb-4">
            {formatCurrency(plan.price_yearly)}/year (save{' '}
            {Math.round((1 - plan.price_yearly / (plan.price_monthly * 12)) * 100)}%)
          </p>
        )}
        <ul className="space-y-2 text-left mb-6">
          {plan.features.map((feature) => (
            <li key={feature} className="flex items-start gap-2 text-sm">
              <Check className="h-4 w-4 text-success-600 dark:text-success-400 shrink-0 mt-0.5" />
              <span>{feature}</span>
            </li>
          ))}
        </ul>
        <Button
          variant={isCurrent ? 'outline' : 'default'}
          className="w-full"
          onClick={() => onSelect(plan)}
          disabled={isCurrent}
        >
          {isCurrent ? 'Current Plan' : 'Select Plan'}
        </Button>
      </CardContent>
    </Card>
  );
}

export default function SubscriptionPage() {
  const router = useRouter();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [loading, setLoading] = useState(true);
  const [changeDialogOpen, setChangeDialogOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<SubscriptionPlan | null>(null);
  const [changing, setChanging] = useState(false);
  const [addCardDialogOpen, setAddCardDialogOpen] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [subRes, plansRes, pmRes] = await Promise.all([
          billingApi.getSubscription(),
          billingApi.listPlans(),
          billingApi.listPaymentMethods(),
        ]);
        setSubscription(subRes.data);
        setPlans(plansRes.data ?? []);
        setPaymentMethods(pmRes.data ?? []);
      } catch (err) {
        console.error('Failed to load subscription data:', err);
        toast.error('Failed to load subscription data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleSelectPlan = (plan: SubscriptionPlan) => {
    setSelectedPlan(plan);
    setChangeDialogOpen(true);
  };

  const handleChangePlan = async () => {
    if (!selectedPlan) return;
    try {
      setChanging(true);
      await billingApi.changePlan({ plan_id: selectedPlan.id });
      toast.success(`Plan changed to ${selectedPlan.name}`);
      setChangeDialogOpen(false);
      // Refresh
      const subRes = await billingApi.getSubscription();
      setSubscription(subRes.data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to change plan');
    } finally {
      setChanging(false);
    }
  };

  const handleSetDefaultPaymentMethod = async (id: string) => {
    try {
      await billingApi.setDefaultPaymentMethod(id);
      toast.success('Default payment method updated');
      const pmRes = await billingApi.listPaymentMethods();
      setPaymentMethods(pmRes.data ?? []);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update payment method');
    }
  };

  const handleRemovePaymentMethod = async (id: string) => {
    try {
      await billingApi.removePaymentMethod(id);
      toast.success('Payment method removed');
      const pmRes = await billingApi.listPaymentMethods();
      setPaymentMethods(pmRes.data ?? []);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to remove payment method');
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
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button + header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Subscription</h1>
          <p className="text-muted-foreground mt-1">
            Manage your plan and billing details
          </p>
        </div>
      </div>

      {/* Current plan */}
      {subscription && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div>
              <CardTitle className="text-xl">Current Plan</CardTitle>
              <CardDescription>
                You are currently on the {subscription.plan.name} plan
              </CardDescription>
            </div>
            <Badge
              variant={statusBadgeVariant[subscription.status] || 'outline'}
              className="capitalize"
            >
              {subscription.status}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border bg-muted/50 p-4">
                <p className="text-sm text-muted-foreground">Price</p>
                <p className="text-2xl font-bold">
                  {formatCurrency(subscription.plan.price_monthly)}
                  <span className="text-sm font-normal text-muted-foreground">/month</span>
                </p>
              </div>
              <div className="rounded-lg border bg-muted/50 p-4">
                <p className="text-sm text-muted-foreground">Period Start</p>
                <p className="text-lg font-semibold">
                  {formatDate(subscription.current_period_start)}
                </p>
              </div>
              <div className="rounded-lg border bg-muted/50 p-4">
                <p className="text-sm text-muted-foreground">Period End</p>
                <p className="text-lg font-semibold">
                  {formatDate(subscription.current_period_end)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Plan comparison */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Compare Plans</h2>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {plans
            .filter((p) => p.is_active)
            .sort((a, b) => a.price_monthly - b.price_monthly)
            .map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                isCurrent={subscription?.plan_id === plan.id}
                onSelect={handleSelectPlan}
              />
            ))}
        </div>
      </div>

      {/* Payment Methods */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-lg">Payment Methods</CardTitle>
            <CardDescription>Manage your payment methods</CardDescription>
          </div>
          <Dialog open={addCardDialogOpen} onOpenChange={setAddCardDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Add Payment Method
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Payment Method</DialogTitle>
                <DialogDescription>
                  Add a new card or payment method to your account.
                </DialogDescription>
              </DialogHeader>
              <div className="py-8 text-center text-muted-foreground">
                <CreditCard className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>Payment method form integrated with your payment provider.</p>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setAddCardDialogOpen(false)}>
                  Cancel
                </Button>
                <Button disabled>Setup Payment Method</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {paymentMethods.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              <CreditCard className="h-8 w-8 mx-auto mb-3 opacity-50" />
              <p className="text-sm">No payment methods on file.</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => setAddCardDialogOpen(true)}
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Payment Method
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {paymentMethods.map((pm) => (
                <div
                  key={pm.id}
                  className={`flex items-center justify-between rounded-lg border p-4 ${
                    pm.is_default ? 'border-primary/50 bg-primary/5' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-muted p-2">
                      <CreditCard className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium capitalize">
                          {pm.brand || pm.type} {pm.last_four ? `**** ${pm.last_four}` : ''}
                        </p>
                        {pm.is_default && (
                          <Badge variant="outline" className="text-xs">Default</Badge>
                        )}
                      </div>
                      {pm.expiry_month && pm.expiry_year && (
                        <p className="text-xs text-muted-foreground">
                          Expires {pm.expiry_month}/{pm.expiry_year}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {!pm.is_default && (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSetDefaultPaymentMethod(pm.id)}
                        >
                          Set Default
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className="text-destructive"
                          onClick={() => handleRemovePaymentMethod(pm.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Change Plan Dialog */}
      <Dialog open={changeDialogOpen} onOpenChange={setChangeDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change Plan</DialogTitle>
            <DialogDescription>
              {selectedPlan && subscription
                ? `Are you sure you want to switch from ${subscription.plan.name} to ${selectedPlan.name}?`
                : 'Select a new plan for your subscription.'}
            </DialogDescription>
          </DialogHeader>

          {selectedPlan && subscription && (
            <div className="space-y-4 py-4">
              <div className="rounded-lg border bg-muted/50 p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Current Plan</span>
                  <span className="font-medium">{subscription.plan.name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">New Plan</span>
                  <span className="font-medium">{selectedPlan.name}</span>
                </div>
                <Separator className="my-2" />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Price change</span>
                  <span className="font-medium">
                    {formatCurrency(selectedPlan.price_monthly - subscription.plan.price_monthly)}
                    /month
                  </span>
                </div>
              </div>
              <div className="rounded-lg border border-warning-200 bg-warning-50 dark:bg-warning-950 dark:border-warning-800 p-3 text-sm text-warning-800 dark:text-warning-200">
                <p>
                  Changes will take effect at the start of the next billing period.
                  You may receive a prorated credit or charge.
                </p>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setChangeDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleChangePlan} disabled={changing}>
              {changing ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Changing...</>
              ) : (
                'Confirm Change'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
