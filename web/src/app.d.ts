// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
declare global {
	namespace App {
		interface Locals {
			/** Authenticated username, null if not logged in */
			user: string | null;
		}
		interface PageData {}
		interface Platform {
			env: {
				/** D1 database binding */
				DB: D1Database;
				/** R2 bucket binding */
				R2: R2Bucket;
				/** Auth secret for session cookie signing */
				AUTH_SECRET: string;
				/** scrypt hash of admin password */
				ADMIN_PASSWORD_HASH: string;
				/** Bearer token for Kiboy ingest API */
				INGEST_TOKEN: string;
			};
			context: { waitUntil(promise: Promise<unknown>): void };
			caches: CacheStorage & { default: Cache };
		}
		interface Error {}
	}
}

export {};
