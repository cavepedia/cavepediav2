import { Auth0Client, filterDefaultIdTokenClaims } from '@auth0/nextjs-auth0/server';

const isProduction = process.env.NODE_ENV === 'production';

export const auth0 = new Auth0Client({
  session: {
    rolling: true,
    absoluteDuration: 60 * 60 * 24 * 7, // 7 days
    inactivityDuration: 60 * 60 * 24, // 1 day
    cookie: {
      secure: isProduction,
      sameSite: 'lax',
    },
  },
  async beforeSessionSaved(session) {
    return {
      ...session,
      user: {
        ...filterDefaultIdTokenClaims(session.user),
        roles: session.user['https://chat.caving.dev/roles']
      }
    };
  }
});
