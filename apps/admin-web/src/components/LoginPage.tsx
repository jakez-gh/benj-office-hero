import React, { useContext, useState, FormEvent } from 'react';
import { AuthContext } from '../auth';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { Label } from './ui/Label';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/Card';
import { Alert, AlertDescription } from './ui/Alert';

export const LoginPage: React.FC = () => {
  const { login } = useContext(AuthContext);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login({ email, password });
    } catch (err) {
      console.error(err);
      setError('Invalid email or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-100 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Wordmark above card */}
        <div className="mb-6 text-center">
          <span className="text-2xl font-bold tracking-tight text-primary-600">
            Office Hero
          </span>
        </div>

        <Card>
          <CardHeader className="pb-4">
            <CardTitle>Sign in</CardTitle>
            <CardDescription>Enter your credentials to access your account</CardDescription>
          </CardHeader>

          <CardContent>
            {error && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  error={!!error}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  error={!!error}
                />
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={loading}
              >
                {loading ? 'Signing in…' : 'Sign in'}
              </Button>
              <p className="text-center text-sm text-neutral-500">
                <a href="mailto:support@officehero.app" className="text-primary-600 hover:underline">
                  Forgot password?
                </a>
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
