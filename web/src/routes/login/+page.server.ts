import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { verifyPassword, createSession } from '$lib/server/auth';

export const load: PageServerLoad = async ({ locals }) => {
	if (locals.user) throw redirect(302, '/dashboard');
	return {};
};

export const actions: Actions = {
	default: async ({ request, cookies, platform }) => {
		const data     = await request.formData();
		const username = (data.get('username') as string ?? '').trim();
		const password = (data.get('password') as string ?? '');

		if (!username || !password) {
			return fail(400, { error: 'Username dan password wajib diisi.' });
		}

		const storedHash = platform?.env?.ADMIN_PASSWORD_HASH ?? '';
		const authSecret = platform?.env?.AUTH_SECRET ?? '';

		// Only "admin" is a valid username.
		if (username !== 'admin' || !storedHash) {
			return fail(401, { error: 'Username atau password salah.' });
		}

		const ok = await verifyPassword(password, storedHash);
		if (!ok) {
			return fail(401, { error: 'Username atau password salah.' });
		}

		const token = await createSession(username, authSecret);
		cookies.set('session', token, {
			path:     '/',
			httpOnly: true,
			secure:   true,
			sameSite: 'strict',
			maxAge:   60 * 60 * 24 * 7,  // 7 days
		});

		throw redirect(302, '/dashboard');
	}
};
