'use client';

import { useState, useEffect } from 'react';
import {
  CreditCard,
  FileText,
  Wallet,
  Loader2,
  Download,
  Plus,
  ArrowUpRight,
  CheckCircle2,
  AlertCircle,
  Clock,
  XCircle,
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/molecules/tabs';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/molecules/select';
import { Skeleton } from '@/components/atoms/skeleton';
import { formatDate, formatCurrency } from '@/lib/utils';
import { billingApi } from '@/lib/api/billing';
import type { Subscription, Invoice, Wallet as WalletType, UsageSummary } from '@/lib/api/billing';
import { toast } from 'sonner';

const statusBadgeVariant: Record<string, 'default' | 'success' | 'warning' | 'destructive' | 'outline' | 'secondary' | 'info'> = {
  active: 'success',
  trialing: 'info',
  past_due: 'warning',
  canceled: 'destructive',
  incomplete: 'outline',
};

const invoiceStatusBadge: Record<string, 'default' | 'success' | 'warning' | 'destructive' | 'outline' | 'secondary' | 'info'> = {
  paid: 'success',
  open: 'info',
  draft: 'outline',
  void: 'secondary',
  uncollectible: 'destructive',
};

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export default function BillingPage() {
  const [activeTab, setActiveTab] = useState('subscriptions');
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [wallet, setWallet] = useState<WalletType | null>(null);
  const [usageSummary, setUsageSummary] = useState<UsageSummary[]>([]);
  const [loading, setLoading] = useState({
    subscription: true,
    invoices: true,
    wallet: true,
  });
  const [invoicePage, setInvoicePage] = useState(1);
  const [invoiceTotal, setInvoiceTotal] = useState(0);
  const [invoiceHasMore, setInvoiceHasMore] = useState(false);
  const [topUpOpen, setTopUpOpen] = useState(false);
  const [topUpAmount, setTopUpAmount] = useState(50);
  const [topingUp, setTopingUp] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  // Load subscription
  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        setLoading((prev) => ({ ...prev, subscription: true }));
        const res = await billingApi.getSubscription();
        setSubscription(res.data);
      } catch (err) {
        console.error('Failed to load subscription:', err);
      } finally {
        setLoading((prev) => ({ ...prev, subscription: false }));
      }
    };
    fetchSubscription();
  }, []);

  // Load invoices
  useEffect(() => {
    const fetchInvoices = async () => {
      try {
        setLoading((prev) => ({ ...prev, invoices: true }));
        const res = await billingApi.listInvoices({ page: invoicePage, limit: 10 });
        setInvoices(res.data);
        setInvoiceTotal(res.meta?.total ?? 0);
        setInvoiceHasMore(res.meta?.has_more ?? false);
      } catch (err) {
        console.error('Failed to load invoices:', err);
      } finally {
        setLoading((prev) => ({ ...prev, invoices: false }));
      }
    };
    if (activeTab === 'invoices') {
      fetchInvoices();
    }
  }, [activeTab, invoicePage]);

  // Load wallet + usage
  useEffect(() => {
    const fetchWalletData = async () => {
      try {
        setLoading((prev) => ({ ...prev, wallet: true }));
        const [walletRes, usageRes] = await Promise.all([
          billingApi.getWallet(),
          billingApi.getUsageSummary(),
        ]);
        setWallet(walletRes.data);
        setUsageSummary(usageRes.data ?? []);
      } catch (err) {
        console.error('Failed to load wallet:', err);
      } finally {
        setLoading((prev) => ({ ...prev, wallet: false }));
      }
    };
    if (activeTab === 'wallet') {
      fetchWalletData();
    }
  }, [activeTab]);

  const handleCancelSubscription = async () => {
    try {
      setCancelling(true);
      await billingApi.cancelSubscription();
      toast.success('Subscription will be canceled at the end of the billing period');
      setCancelDialogOpen(false);
      // Refresh
      const res = await billingApi.getSubscription();
      setSubscription(res.data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to cancel subscription');
    } finally {
      setCancelling(false);
    }
  };

  const handleReactivate = async () => {
    try {
      await billingApi.reactivateSubscription();
      toast.success('Subscription reactivated');
      const res = await billingApi.getSubscription();
      setSubscription(res.data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to reactivate subscription');
    }
  };

  const handleTopUp = async () => {
    try {
      setTopingUp(true);
      await billingApi.addWalletCredit(topUpAmount);
      toast.success(`$${topUpAmount} added to your wallet`);
      setTopUpOpen(false);
      const res = await billingApi.getWallet();
      setWallet(res.data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to add credit');
    } finally {
      setTopingUp(false);
    }
  };

  const handleDownloadInvoice = async (invoiceId: string) => {
    try {
      const blob = await billingApi.downloadInvoice(invoiceId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invoice-${invoiceId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('Invoice downloaded');
    } catch (err) {
      toast.error('Failed to download invoice');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Billing</h1>
        <p className="text-muted-foreground mt-1">
          Manage your subscription, invoices, and wallet
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3 lg:w-[400px]">
          <TabsTrigger value="subscriptions">
            <CreditCard className="mr-2 h-4 w-4" /> Subscriptions
          </TabsTrigger>
          <TabsTrigger value="invoices">
            <FileText className="mr-2 h-4 w-4" /> Invoices
          </TabsTrigger>
          <TabsTrigger value="wallet">
            <Wallet className="mr-2 h-4 w-4" /> Wallet
          </TabsTrigger>
        </TabsList>

        {/* ─── SUBSCRIPTIONS TAB ─── */}
        <TabsContent value="subscriptions" className="space-y-4 mt-6">
          {loading.subscription ? (
            <Card>
              <CardHeader>
                <Skeleton className="h-6 w-48" />
                <Skeleton className="h-4 w-64" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-32 w-full" />
              </CardContent>
            </Card>
          ) : subscription ? (
            <>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <div>
                    <CardTitle className="text-xl">{subscription.plan.name} Plan</CardTitle>
                    <CardDescription>
                      {subscription.plan.description}
                    </CardDescription>
                  </div>
                  <Badge
                    variant={statusBadgeVariant[subscription.status] || 'outline'}
                    className="capitalize"
                  >
                    {subscription.cancel_at_period_end
                      ? 'Canceling'
                      : subscription.status}
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="rounded-lg border bg-muted/50 p-4">
                      <p className="text-sm text-muted-foreground">Price</p>
                      <p className="text-2xl font-bold">
                        {formatCurrency(subscription.plan.price_monthly)}
                        <span className="text-sm font-normal text-muted-foreground">/month</span>
                      </p>
                    </div>
                    <div className="rounded-lg border bg-muted/50 p-4">
                      <p className="text-sm text-muted-foreground">Current Period End</p>
                      <p className="text-lg font-semibold">
                        {formatDate(subscription.current_period_end)}
                      </p>
                    </div>
                    <div className="rounded-lg border bg-muted/50 p-4">
                      <p className="text-sm text-muted-foreground">Billing Anchor</p>
                      <p className="text-lg font-semibold capitalize">
                        {subscription.billing_anchor.replace('_', ' ')}
                      </p>
                    </div>
                  </div>

                  {subscription.cancel_at_period_end && (
                    <div className="flex items-center gap-2 rounded-lg border border-warning-200 bg-warning-50 dark:bg-warning-950 dark:border-warning-800 p-3 text-sm text-warning-800 dark:text-warning-200">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      <span>
                        Your subscription will be canceled at the end of the current billing period (
                        {formatDate(subscription.current_period_end)}).
                      </span>
                    </div>
                  )}

                  <div className="flex items-center gap-3 pt-2">
                    {subscription.cancel_at_period_end ? (
                      <Button onClick={handleReactivate}>
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Reactivate Subscription
                      </Button>
                    ) : (
                      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
                        <DialogTrigger asChild>
                          <Button variant="outline" className="text-destructive hover:text-destructive">
                            <XCircle className="mr-2 h-4 w-4" />
                            Cancel Subscription
                          </Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>Cancel Subscription</DialogTitle>
                            <DialogDescription>
                              Are you sure you want to cancel your {subscription.plan.name} plan?
                              Your subscription will remain active until the end of the current
                              billing period ({formatDate(subscription.current_period_end)}).
                            </DialogDescription>
                          </DialogHeader>
                          <DialogFooter>
                            <Button variant="outline" onClick={() => setCancelDialogOpen(false)}>
                              Keep Subscription
                            </Button>
                            <Button
                              variant="destructive"
                              onClick={handleCancelSubscription}
                              disabled={cancelling}
                            >
                              {cancelling ? (
                                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Canceling...</>
                              ) : (
                                'Cancel Subscription'
                              )}
                            </Button>
                          </DialogFooter>
                        </DialogContent>
                      </Dialog>
                    )}
                    <Button variant="outline" asChild>
                      <a href="/billing/subscription">
                        <ArrowUpRight className="mr-2 h-4 w-4" />
                        Manage Plan
                      </a>
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Plan features */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Plan Features</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {subscription.plan.features.map((feature) => (
                      <div key={feature} className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-success-600 dark:text-success-400 shrink-0" />
                        <span className="text-sm">{feature}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>No Active Subscription</CardTitle>
                <CardDescription>You don&apos;t have an active subscription.</CardDescription>
              </CardHeader>
              <CardContent>
                <Button asChild>
                  <a href="/billing/subscription">View Plans</a>
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ─── INVOICES TAB ─── */}
        <TabsContent value="invoices" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Invoices</CardTitle>
              <CardDescription>View and download your invoices</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Invoice #</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="hidden md:table-cell">Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="hidden md:table-cell">Due Date</TableHead>
                    <TableHead className="w-[60px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading.invoices ? (
                    Array.from({ length: 5 }).map((_, i) => (
                      <TableRow key={i}>
                        <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-28" /></TableCell>
                        <TableCell className="hidden md:table-cell"><Skeleton className="h-5 w-20" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                        <TableCell className="hidden md:table-cell"><Skeleton className="h-5 w-28" /></TableCell>
                        <TableCell><Skeleton className="h-8 w-8" /></TableCell>
                      </TableRow>
                    ))
                  ) : invoices.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                        No invoices found
                      </TableCell>
                    </TableRow>
                  ) : (
                    invoices.map((invoice) => (
                      <TableRow key={invoice.id}>
                        <TableCell className="font-medium">{invoice.number}</TableCell>
                        <TableCell>{formatDate(invoice.created_at)}</TableCell>
                        <TableCell className="hidden md:table-cell">
                          {formatCurrency(invoice.amount_due, invoice.currency)}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={invoiceStatusBadge[invoice.status] || 'outline'}
                            className="capitalize"
                          >
                            {invoice.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="hidden md:table-cell text-muted-foreground">
                          {formatDate(invoice.due_date)}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => handleDownloadInvoice(invoice.id)}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Pagination */}
          {!loading.invoices && invoices.length > 0 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Page {invoicePage} of {Math.ceil(invoiceTotal / 10)} ({invoiceTotal} total)
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={invoicePage <= 1}
                  onClick={() => setInvoicePage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!invoiceHasMore}
                  onClick={() => setInvoicePage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}

          <div className="text-center">
            <Button variant="outline" asChild>
              <a href="/billing/invoices">
                <FileText className="mr-2 h-4 w-4" />
                View All Invoices
              </a>
            </Button>
          </div>
        </TabsContent>

        {/* ─── WALLET TAB ─── */}
        <TabsContent value="wallet" className="space-y-4 mt-6">
          {loading.wallet ? (
            <Card>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-24 w-full" />
              </CardContent>
            </Card>
          ) : (
            <>
              {/* Balance card */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-lg">Credit Balance</CardTitle>
                  <Wallet className="h-5 w-5 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-3xl font-bold">
                        {wallet ? formatCurrency(wallet.balance, wallet.currency) : '$0'}
                      </p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Available credit
                      </p>
                    </div>
                    <Dialog open={topUpOpen} onOpenChange={setTopUpOpen}>
                      <DialogTrigger asChild>
                        <Button>
                          <Plus className="mr-2 h-4 w-4" />
                          Top Up
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Add Credit</DialogTitle>
                          <DialogDescription>
                            Add funds to your wallet to pay for usage-based services.
                          </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                          <div className="space-y-2">
                            <Label htmlFor="amount">Amount (USD)</Label>
                            <Input
                              id="amount"
                              type="number"
                              min={10}
                              step={10}
                              value={topUpAmount}
                              onChange={(e) => setTopUpAmount(Number(e.target.value))}
                            />
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {[25, 50, 100, 250, 500].map((amt) => (
                              <Button
                                key={amt}
                                variant={topUpAmount === amt ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => setTopUpAmount(amt)}
                              >
                                ${amt}
                              </Button>
                            ))}
                          </div>
                        </div>
                        <DialogFooter>
                          <Button variant="outline" onClick={() => setTopUpOpen(false)}>
                            Cancel
                          </Button>
                          <Button onClick={handleTopUp} disabled={topingUp || topUpAmount < 10}>
                            {topingUp ? (
                              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Processing...</>
                            ) : (
                              <>Add ${topUpAmount}</>
                            )}
                          </Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                  </div>
                </CardContent>
              </Card>

              {/* Usage summary */}
              {usageSummary.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Current Period Usage</CardTitle>
                    <CardDescription>
                      Usage summary for the current billing period
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {usageSummary.map((usage) => (
                        <div key={usage.metric_name}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium capitalize">
                              {usage.metric_name.replace(/_/g, ' ')}
                            </span>
                            <span className="text-sm text-muted-foreground">
                              {usage.total_quantity} {usage.unit}
                            </span>
                          </div>
                          <div className="h-2 rounded-full bg-muted overflow-hidden">
                            <div
                              className="h-full rounded-full bg-primary"
                              style={{
                                width: `${Math.min(100, (usage.total_quantity / 10000) * 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
