'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search,
  Plus,
  Filter,
  ArrowUpDown,
  MoreHorizontal,
  ChevronLeft,
  ChevronRight,
  Trash2,
  Edit,
} from 'lucide-react';
import { useCustomFields, useCreateCustomField, useUpdateCustomField, useDeleteCustomField } from '@/hooks/use-custom-fields';
import { Button } from '@/components/atoms/button';
import { Input } from '@/components/atoms/input';
import { Badge } from '@/components/atoms/badge';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/molecules/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/molecules/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/molecules/dialog';
import { Label } from '@/components/atoms/label';
import { Skeleton } from '@/components/atoms/skeleton';
import { formatDate } from '@/lib/utils';
import { toast } from 'sonner';
import type {
  CustomFieldDefinition,
  CreateCustomFieldDefinitionRequest,
  UpdateCustomFieldDefinitionRequest,
  CustomFieldType,
} from '@/types';

const fieldTypeColors: Record<CustomFieldType, string> = {
  text: 'bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-100',
  number: 'bg-info-100 text-info-800 dark:bg-info-900 dark:text-info-100',
  date: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100',
  dropdown: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-100',
  multi_select: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100',
  url: 'bg-secondary-100 text-secondary-800 dark:bg-secondary-900 dark:text-secondary-100',
};

const fieldTypes: CustomFieldType[] = ['text', 'number', 'date', 'dropdown', 'multi_select', 'url'];

interface CustomFieldFormState {
  name: string;
  key: string;
  description: string;
  field_type: CustomFieldType;
  config: Record<string, unknown>;
  is_required: boolean;
  is_active: boolean;
  display_order: number;
}

const emptyForm: CustomFieldFormState = {
  name: '',
  key: '',
  description: '',
  field_type: 'text',
  config: {},
  is_required: false,
  is_active: true,
  display_order: 0,
};

export default function CustomFieldsPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [isActiveFilter, setIsActiveFilter] = useState<boolean | undefined>(undefined);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  [form, setForm] = useState<CustomFieldFormState>(emptyForm);
  [editId, setEditId] = useState<string | null>(null);

  const { data, isLoading, error } = useCustomFields({
    page,
    limit: 25,
    search: search || undefined,
    is_active: isActiveFilter,
  });

  const createCustomField = useCreateCustomField();
  const updateCustomField = useUpdateCustomField('');
  const deleteCustomField = useDeleteCustomField();

  const customFields = data?.data ?? [];
  const meta = data?.meta;

  const updateField = (field: keyof CustomFieldFormState, value: string | boolean | number | Record<string, unknown>) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreateCustomField = async () => {
    if (!form.name || !form.key) {
      toast.error('Name and key are required');
      return;
    }

    try {
      const payload: CreateCustomFieldDefinitionRequest = {
        name: form.name,
        key: form.key,
        description: form.description || undefined,
        field_type: form.field_type,
        config: Object.keys(form.config).length > 0 ? form.config : undefined,
        is_required: form.is_required,
        is_active: form.is_active,
        display_order: form.display_order,
      };

      await createCustomField.mutateAsync(payload);
      toast.success('Custom field created successfully');
      setCreateDialogOpen(false);
      setForm(emptyForm);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create custom field');
    }
  };

  const handleUpdateCustomField = async () => {
    if (!editId) return;

    if (!form.name || !form.key) {
      toast.error('Name and key are required');
      return;
    }

    try {
      const payload: UpdateCustomFieldDefinitionRequest = {
        name: form.name,
        key: form.key,
        description: form.description || undefined,
        field_type: form.field_type,
        config: Object.keys(form.config).length > 0 ? form.config : undefined,
        is_required: form.is_required,
        is_active: form.is_active,
        display_order: form.display_order,
      };

      await updateCustomField.mutateAsync(payload);
      toast.success('Custom field updated successfully');
      setEditDialogOpen(false);
      setEditId(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update custom field');
    }
  };

  const handleDeleteCustomField = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this custom field? This action cannot be undone.')) {
      return;
    }

    try {
      await deleteCustomField.mutateAsync(id);
      toast.success('Custom field deleted successfully');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete custom field');
    }
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Custom Fields</h1>
          <p className="text-muted-foreground mt-1">
            Manage custom fields for your workspace
          </p>
        </div>
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Add Custom Field
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[550px]">
            <DialogHeader>
              <DialogTitle>New Custom Field</DialogTitle>
              <DialogDescription>
                Create a new custom field for contacts and deals
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  placeholder="Enter field name"
                  value={form.name}
                  onChange={(e) => updateField('name', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="key">Key *</Label>
                <Input
                  id="key"
                  placeholder="Enter field key (used in API)"
                  value={form.key}
                  onChange={(e) => updateField('key', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  placeholder="Enter field description"
                  value={form.description}
                  onChange={(e) => updateField('description', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Field Type</Label>
                <Select
                  value={form.field_type}
                  onValueChange={(v) => updateField('field_type', v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select field type" />
                  </SelectTrigger>
                  <SelectContent>
                    {fieldTypes.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="config">Configuration (JSON)</Label>
                <Input
                  id="config"
                  type="text"
                  placeholder='{"option1": "Value 1", "option2": "Value 2"} (for dropdown/multi_select)'
                  value={JSON.stringify(form.config)}
                  onChange={(e) => {
                    try {
                      const parsed = JSON.parse(e.target.value);
                      updateField('config', parsed);
                    } catch (err) {
                      // Invalid JSON, keep current value
                    }
                  }}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Required</Label>
                  <Select
                    value={form.is_required ? 'true' : 'false'}
                    onValueChange={(v) => updateField('is_required', v === 'true')}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="true">Yes</SelectItem>
                      <SelectItem value="false">No</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Active</Label>
                  <Select
                    value={form.is_active ? 'true' : 'false'}
                    onValueChange={(v) => updateField('is_active', v === 'true')}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="true">Yes</SelectItem>
                      <SelectItem value="false">No</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Display Order</Label>
                <Input
                  id="display_order"
                  type="number"
                  min="0"
                  placeholder="0"
                  value={form.display_order.toString()}
                  onChange={(e) => updateField('display_order', parseInt(e.target.value) || 0)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                onClick={handleCreateCustomField}
                disabled={createCustomField.isPending}
              >
                {createCustomField.isPending ? 'Creating...' : 'Create Custom Field'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search + Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search custom fields..."
            className="pl-9"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select value={isActiveFilter ?? ''} onValueChange={(v) => { setIsActiveFilter(v === '' ? undefined : v === 'true'); setPage(1); }}>
          <SelectTrigger className="w-[120px]">
            <SelectValue placeholder="Active Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All</SelectItem>
            <SelectItem value="true">Active Only</SelectItem>
            <SelectItem value="false">Inactive Only</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Data Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[200px]">
                  <button className="flex items-center gap-1 hover:text-foreground">
                    Name <ArrowUpDown className="h-3 w-3" />
                  </button>
                </TableHead>
                <TableHead className="w-[120px]">
                  <button className="flex items-center gap-1 hover:text-foreground">
                    Key <ArrowUpDown className="h-3 w-3" />
                  </button>
                </TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="w-[100px]">Order</TableHead>
                <TableHead className="w-[80px]">Required</TableHead>
                <TableHead className="w-[80px]">Active</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-8 w-8 rounded-full" /></TableCell>
                  </TableRow>
                ))
              ) : error ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-12 text-destructive">
                    Failed to load custom fields. Please try again.
                  </TableCell>
                </TableRow>
              ) : customFields.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                    No custom fields found
                  </TableCell>
                </TableRow>
              ) : (
                customFields.map((field: CustomFieldDefinition) => (
                  <TableRow
                    key={field.id}
                    className="cursor-pointer hover:bg-muted"
                    onClick={() => {
                      // Handle row click to edit
                      setEditId(field.id);
                      setForm({
                        name: field.name,
                        key: field.key,
                        description: field.description ?? '',
                        field_type: field.field_type,
                        config: field.config,
                        is_required: field.is_required,
                        is_active: field.is_active,
                        display_order: field.display_order,
                      });
                      setEditDialogOpen(true);
                    }}
                  >
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="flex flex-col">
                          <p className="font-medium">{field.name}</p>
                          <p className="text-xs text-muted-foreground">{field.key}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{field.key}</TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={fieldTypeColors[field.field_type]}
                      >
                        {field.field_type.charAt(0).toUpperCase() + field.field_type.slice(1).replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">{field.display_order}</TableCell>
                    <TableCell className="text-center">
                      <Badge
                        variant={field.is_required ? 'default' : 'outline'}
                        className={field.is_required
                          ? 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100'
                          : 'bg-muted text-muted-foreground'}
                      >
                        {field.is_required ? 'Yes' : 'No'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge
                        variant={field.is_active ? 'default' : 'outline'}
                        className={field.is_active
                          ? 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100'
                          : 'bg-muted text-muted-foreground'}
                      >
                        {field.is_active ? 'Yes' : 'No'}
                      </Badge>
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
                          <DropdownMenuItem onClick={() => {
                            setEditId(field.id);
                            setForm({
                              name: field.name,
                              key: field.key,
                              description: field.description ?? '',
                              field_type: field.field_type,
                              config: field.config,
                              is_required: field.is_required,
                              is_active: field.is_active,
                              display_order: field.display_order,
                            });
                            setEditDialogOpen(true);
                          }}>
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem className="text-destructive" onClick={() => handleDeleteCustomField(field.id)}>
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination */}
      {meta && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing page {meta.page} of {Math.ceil(meta.total / meta.per_page)} ({meta.total} total)
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!meta.has_more}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogTrigger asChild>
          <div />
        </DialogTrigger>
        <DialogContent className="sm:max-w-[550px]">
          <DialogHeader>
            <DialogTitle>Edit Custom Field</DialogTitle>
            <DialogDescription>
              Modify the custom field settings
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit_name">Name *</Label>
              <Input
                id="edit_name"
                placeholder="Enter field name"
                value={form.name}
                onChange={(e) => updateField('name', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_key">Key *</Label>
              <Input
                id="edit_key"
                placeholder="Enter field key (used in API)"
                value={form.key}
                onChange={(e) => updateField('key', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_description">Description</Label>
              <Input
                id="edit_description"
                placeholder="Enter field description"
                value={form.description}
                onChange={(e) => updateField('description', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Field Type</Label>
              <Select
                value={form.field_type}
                onValueChange={(v) => updateField('field_type', v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select field type" />
                </SelectTrigger>
                <SelectContent>
                  {fieldTypes.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_config">Configuration (JSON)</Label>
              <Input
                id="edit_config"
                type="text"
                placeholder='{"option1": "Value 1", "option2": "Value 2"} (for dropdown/multi_select)'
                value={JSON.stringify(form.config)}
                onChange={(e) => {
                  try {
                    const parsed = JSON.parse(e.target.value);
                    updateField('config', parsed);
                  } catch (err) {
                    // Invalid JSON, keep current value
                  }
                }}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Required</Label>
                <Select
                  value={form.is_required ? 'true' : 'false'}
                  onValueChange={(v) => updateField('is_required', v === 'true')}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="true">Yes</SelectItem>
                    <SelectItem value="false">No</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Active</Label>
                <Select
                  value={form.is_active ? 'true' : 'false'}
                  onValueChange={(v) => updateField('is_active', v === 'true')}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="true">Yes</SelectItem>
                    <SelectItem value="false">No</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Display Order</Label>
              <Input
                id="edit_display_order"
                type="number"
                min="0"
                placeholder="0"
                value={form.display_order.toString()}
                onChange={(e) => updateField('display_order', parseInt(e.target.value) || 0)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setEditDialogOpen(false);
              setEditId(null);
              setForm(emptyForm);
            }}>
              Cancel
            </Button>
            <Button
              type="submit"
              onClick={handleUpdateCustomField}
              disabled={updateCustomField.isPending}
            >
              {updateCustomField.isPending ? 'Updating...' : 'Update Custom Field'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}