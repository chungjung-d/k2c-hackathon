import { Pool } from "pg";

const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  throw new Error("DATABASE_URL is not set");
}

declare global {
  var __k2cDbPool: Pool | undefined;
}

const pool = globalThis.__k2cDbPool ?? new Pool({ connectionString });

if (process.env.NODE_ENV !== "production") {
  globalThis.__k2cDbPool = pool;
}

export async function query<T = unknown>(
  text: string,
  params: Array<unknown> = [],
): Promise<{ rows: T[] }> {
  const client = await pool.connect();
  try {
    const result = await client.query(text, params);
    return { rows: result.rows as T[] };
  } finally {
    client.release();
  }
}
