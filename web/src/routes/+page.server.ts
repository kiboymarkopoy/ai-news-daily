import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// Root redirect — if logged in go to dashboard, else login.
export const load: PageServerLoad = async ({ locals }) => {
	if (locals.user) throw redirect(302, '/dashboard');
	throw redirect(302, '/login');
};
