import { Auth0Client, filterDefaultIdTokenClaims } from '@auth0/nextjs-auth0/server';

export const auth0 = new Auth0Client({
  async beforeSessionSaved(session, idToken) {
    return {
      ...session,
      user: {
        ...filterDefaultIdTokenClaims(session.user),
        roles: session.user['https://chat.caving.dev/roles']
      }
    };
  }
});
