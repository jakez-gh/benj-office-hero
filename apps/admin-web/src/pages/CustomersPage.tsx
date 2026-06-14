import { useEffect, useState } from 'react';
import {
  createCustomer,
  listCustomers,
  type CustomerCreate,
  type CustomerSummary,
} from '@office-hero/api-client';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Label } from '../components/ui/Label';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '../components/ui/Table';
import { Skeleton } from '../components/ui/Skeleton';
import { Alert, AlertDescription } from '../components/ui/Alert';
import { ErrorBanner } from '../components/ui/ErrorBanner';

function AddCustomerModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (customer: CustomerSummary) => void;
}) {
  const [form, setForm] = useState<CustomerCreate>({ name: '' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const created = await createCustomer(form);
      onCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold text-neutral-900">New Customer</h2>
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="customer-name">Name *</Label>
            <Input
              id="customer-name"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Acme Plumbing Supplies"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="customer-email">Email</Label>
              <Input
                id="customer-email"
                type="email"
                value={form.email ?? ''}
                onChange={(e) =>
                  setForm((f) => ({ ...f, email: e.target.value || undefined }))
                }
                placeholder="contact@example.com"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="customer-phone">Phone</Label>
              <Input
                id="customer-phone"
                type="tel"
                value={form.phone ?? ''}
                onChange={(e) =>
                  setForm((f) => ({ ...f, phone: e.target.value || undefined }))
                }
                placeholder="(555) 123-4567"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="customer-notes">Notes</Label>
            <Input
              id="customer-notes"
              value={form.notes ?? ''}
              onChange={(e) =>
                setForm((f) => ({ ...f, notes: e.target.value || undefined }))
              }
              placeholder="Optional"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create customer'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function CustomersPage() {
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  // Debounce: propagate search to debouncedSearch after 300ms of quiet
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Fetch customers when debouncedSearch changes; loading starts true so no
  // setState is called synchronously at effect top (satisfies react-hooks/set-state-in-effect)
  useEffect(() => {
    let cancelled = false;
    listCustomers({ search: debouncedSearch || undefined })
      .then(r => {
        if (!cancelled) {
          setCustomers(r.items);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedSearch]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-neutral-900">Customers</h1>
        <Button onClick={() => setShowAdd(true)}>+ Add Customer</Button>
      </div>

      <Input
        placeholder="Search customers…"
        value={search}
        onChange={e => setSearch(e.target.value)}
        className="max-w-sm"
      />

      {error && <ErrorBanner error={error} />}

      {loading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : customers.length === 0 ? (
        <div className="text-center py-12 text-neutral-500">
          No customers yet. Add your first customer to get started.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>City</TableHead>
              <TableHead>Phone</TableHead>
              <TableHead>Locations</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {customers.map(c => (
              <TableRow key={c.id}>
                <TableCell className="font-medium">{c.name}</TableCell>
                <TableCell>{c.primary_city ?? '—'}</TableCell>
                <TableCell>{c.phone ?? '—'}</TableCell>
                <TableCell>{c.location_count}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {showAdd && (
        <AddCustomerModal
          onClose={() => setShowAdd(false)}
          onCreated={(customer) => {
            setShowAdd(false);
            setCustomers((prev) => [customer, ...prev]);
          }}
        />
      )}
    </div>
  );
}
