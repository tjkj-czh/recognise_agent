import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import pg from 'pg'

const __dirname = dirname(fileURLToPath(import.meta.url))
const { Pool } = pg

const pool = new Pool({
  host: process.env.DB_HOST || '10.10.6.161',
  port: parseInt(process.env.DB_PORT || '5432', 10),
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'Zjzzb',
  database: process.env.DB_NAME || 'postgres',
})

async function run() {
  const client = await pool.connect()
  try {
    console.log('Connected to database')

    // Run init migration
    const initSql = readFileSync(join(__dirname, '001_init.sql'), 'utf-8')
    await client.query(initSql)
    console.log('✓ Tables created')

    // Seed users
    const usersSql = readFileSync(join(__dirname, '../seed/users.sql'), 'utf-8')
    await client.query(usersSql)
    console.log('✓ Users seeded')

    // Seed land supplies
    const landSql = readFileSync(join(__dirname, '../seed/land-supplies.sql'), 'utf-8')
    await client.query(landSql)
    console.log('✓ Land supplies seeded')

    console.log('\nAll migrations completed successfully!')
  } catch (err) {
    console.error('Migration failed:', err)
    process.exit(1)
  } finally {
    client.release()
    await pool.end()
  }
}

run()
