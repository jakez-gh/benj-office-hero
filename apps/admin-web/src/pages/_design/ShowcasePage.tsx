import React from 'react';
import {
  Alert,
  AlertDescription,
  AlertTitle,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui';

const Section: React.FC<{ id: string; title: string; children: React.ReactNode }> = ({
  id,
  title,
  children,
}) => (
  <section id={id} className="space-y-4">
    <h2 className="text-xl font-semibold tracking-tight text-neutral-900">{title}</h2>
    <div className="rounded-card border border-neutral-200 bg-white p-6 shadow-sm">
      {children}
    </div>
  </section>
);

export const ShowcasePage: React.FC = () => {
  return (
    <div className="min-h-screen bg-neutral-50 px-6 py-10">
      <div className="mx-auto max-w-5xl space-y-10">
        <header className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-primary-600">
            Office Hero · Design System
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-neutral-900">
            UI primitives showcase
          </h1>
          <p className="max-w-2xl text-sm text-neutral-600">
            Dev-only reference page. Renders every primitive shipped in
            <code className="ml-1 rounded bg-neutral-100 px-1.5 py-0.5 text-xs">
              src/components/ui
            </code>
            . Not linked from production navigation.
          </p>
        </header>

        <Section id="buttons" title="Button">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="default">Default</Button>
              <Button variant="outline">Outline</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="destructive">Destructive</Button>
              <Button disabled>Disabled</Button>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button size="sm">Small</Button>
              <Button size="md">Medium</Button>
              <Button size="lg">Large</Button>
            </div>
          </div>
        </Section>

        <Section id="inputs" title="Input + Label">
          <form
            className="grid max-w-md gap-4"
            onSubmit={(e) => e.preventDefault()}
          >
            <div className="grid gap-1.5">
              <Label htmlFor="showcase-email">Email</Label>
              <Input
                id="showcase-email"
                type="email"
                placeholder="you@example.com"
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="showcase-error">Error state</Label>
              <Input
                id="showcase-error"
                type="text"
                defaultValue="invalid value"
                error
              />
              <p className="text-xs text-danger-600">This field is required.</p>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="showcase-disabled">Disabled</Label>
              <Input id="showcase-disabled" disabled defaultValue="read-only" />
            </div>
          </form>
        </Section>

        <Section id="cards" title="Card">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Open jobs today</CardTitle>
                <CardDescription>
                  Six dispatched, two awaiting parts.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold text-neutral-900">8</p>
              </CardContent>
              <CardFooter>
                <Button variant="outline" size="sm">
                  View board
                </Button>
              </CardFooter>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Vehicles in service</CardTitle>
                <CardDescription>
                  Fleet status across the active depot.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold text-neutral-900">12</p>
              </CardContent>
              <CardFooter>
                <Button variant="ghost" size="sm">
                  Manage fleet
                </Button>
              </CardFooter>
            </Card>
          </div>
        </Section>

        <Section id="alerts" title="Alert">
          <div className="space-y-3">
            <Alert>
              <AlertTitle>Heads up</AlertTitle>
              <AlertDescription>
                Default informational message rendered above the form.
              </AlertDescription>
            </Alert>
            <Alert variant="success">
              <AlertTitle>Saved</AlertTitle>
              <AlertDescription>
                Your changes were saved successfully.
              </AlertDescription>
            </Alert>
            <Alert variant="warning">
              <AlertTitle>Check this</AlertTitle>
              <AlertDescription>
                Three vehicles need an inspection in the next 14 days.
              </AlertDescription>
            </Alert>
            <Alert variant="destructive">
              <AlertTitle>Something went wrong</AlertTitle>
              <AlertDescription>
                We could not reach the dispatch server. Try again shortly.
              </AlertDescription>
            </Alert>
          </div>
        </Section>

        <Section id="skeletons" title="Skeleton">
          <div className="space-y-3">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-24 w-full" />
          </div>
        </Section>

        <Section id="tables" title="Table">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Job</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell className="font-medium">JOB-1043</TableCell>
                <TableCell>Acme Plumbing</TableCell>
                <TableCell>Dispatched</TableCell>
                <TableCell className="text-right">$420.00</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">JOB-1044</TableCell>
                <TableCell>North Side HVAC</TableCell>
                <TableCell>Scheduled</TableCell>
                <TableCell className="text-right">$1,180.00</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">JOB-1045</TableCell>
                <TableCell>Riverside Cafe</TableCell>
                <TableCell>Completed</TableCell>
                <TableCell className="text-right">$95.00</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Section>
      </div>
    </div>
  );
};

export default ShowcasePage;
