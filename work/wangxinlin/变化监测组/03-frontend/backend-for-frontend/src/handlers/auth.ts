import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify'
import bcrypt from 'bcryptjs'
import { query } from '../database.js'

export async function authRoutes(fastify: FastifyInstance) {
  fastify.post('/login', async (request: FastifyRequest<{ Body: { username: string; password: string } }>, reply: FastifyReply) => {
    const { username, password } = request.body

    if (!username || !password) {
      return reply.status(400).send({ message: 'Username and password are required' })
    }

    const result = await query(
      `SELECT u.id, u.username, u.password_hash, u.real_name, r.name as role_name
       FROM users u
       JOIN roles r ON u.role_id = r.id
       WHERE u.username = $1 AND u.status = 'active'`,
      [username]
    )

    if (result.rows.length === 0) {
      return reply.status(401).send({ message: 'Invalid credentials' })
    }

    const user = result.rows[0]
    const valid = await bcrypt.compare(password, user.password_hash)

    if (!valid) {
      return reply.status(401).send({ message: 'Invalid credentials' })
    }

    const token = fastify.jwt.sign({
      id: user.id,
      username: user.username,
      role: user.role_name,
    })

    return {
      token,
      user: {
        id: user.id,
        username: user.username,
        realName: user.real_name,
        role: user.role_name,
      },
    }
  })

  fastify.get('/me', { preHandler: fastify.authenticate }, async (request: FastifyRequest, reply: FastifyReply) => {
    const payload = request.user as { id: number }
    const result = await query(
      `SELECT u.id, u.username, u.real_name, r.name as role_name
       FROM users u
       JOIN roles r ON u.role_id = r.id
       WHERE u.id = $1`,
      [payload.id]
    )

    if (result.rows.length === 0) {
      return reply.status(404).send({ message: 'User not found' })
    }

    const user = result.rows[0]
    return {
      id: user.id,
      username: user.username,
      realName: user.real_name,
      role: user.role_name,
    }
  })
}
