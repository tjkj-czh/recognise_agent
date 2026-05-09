import pg from 'pg'

const { Pool } = pg

const pool = new Pool({
  host: '10.10.6.161',
  port: 5432,
  user: 'postgres',
  password: 'Zjzzb',
  database: 'postgres',
})

const hashes = [
  ['admin', '$2b$10$qmpfbyprScvFsIafmtSGKubonH6NRajOValLJZSaK4eI7QtTdLBbW'],
  ['monitor', '$2b$10$Th.If9HwoWagnS/repwLfuR.ifEEhm04Qfri0K2Wkia8JoryfDc/G'],
  ['guest', '$2b$10$.EMF.0u8RoTu1OnR5xJDq.mrgRPcFECSfRv1On3OGoMlvGRt7waje'],
]

async function main() {
  for (const [user, hash] of hashes) {
    await pool.query('UPDATE users SET password_hash = $1 WHERE username = $2', [hash, user])
  }
  const res = await pool.query('SELECT username, password_hash FROM users')
  console.log(res.rows)
  await pool.end()
}

main().catch(console.error)
