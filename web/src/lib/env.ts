// Environment variable validation for production

const requiredEnvVars = [
  'AUTH0_SECRET',
  'AUTH0_DOMAIN',
  'AUTH0_CLIENT_ID',
  'AUTH0_CLIENT_SECRET',
  'APP_BASE_URL',
] as const;

const optionalEnvVars = [
  'AGENT_URL',
] as const;

export function validateEnv() {
  const missing: string[] = [];

  for (const envVar of requiredEnvVars) {
    if (!process.env[envVar]) {
      missing.push(envVar);
    }
  }

  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missing.join(', ')}\n` +
      'Please check your .env.local file or environment configuration.'
    );
  }
}

export function getEnv() {
  return {
    auth0: {
      secret: process.env.AUTH0_SECRET!,
      domain: process.env.AUTH0_DOMAIN!,
      clientId: process.env.AUTH0_CLIENT_ID!,
      clientSecret: process.env.AUTH0_CLIENT_SECRET!,
    },
    appBaseUrl: process.env.APP_BASE_URL!,
    agentUrl: process.env.AGENT_URL || 'http://localhost:8000/',
    isProduction: process.env.NODE_ENV === 'production',
  };
}
