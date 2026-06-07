import type { Handle } from '@sveltejs/kit';
import { verifySession } from '$lib/server/auth';

const PUBLIC_PATHS = ['/login', '/api/ingest'];

export const handle: Handle = async ({ event, resolve }) => {
	// Extract user from session cookie on every request.
	const sessionCookie = event.cookies.get('session');
	const authSecret = event.platform?.env?.AUTH_SECRET ?? '';
	event.locals.user = sessionCookie
		? await verifySession(sessionCookie, authSecret)
		: null;

	// Guard all non-public routes.
	const path = event.url.pathname;
	const isPublic = PUBLIC_PATHS.some((p) => path === p || path.startsWith(p + '/'));

	if (!isPublic && !event.locals.user) {
		return new Response(null, {
			status: 302,
			headers: { location: '/login' }
		});
	}

	return resolve(event);
};
