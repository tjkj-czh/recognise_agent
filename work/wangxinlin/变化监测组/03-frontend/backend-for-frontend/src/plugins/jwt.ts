import fp from 'fastify-plugin'
import jwt from '@fastify/jwt'
import type { FastifyInstance } from 'fastify'
import { config } from '../config.js'

export default fp(async function (fastify: FastifyInstance) {
  await fastify.register(jwt, {
    secret: config.jwtSecret,
    sign: { expiresIn: '7d' },
  })

  fastify.decorate('authenticate', async function (request, reply) {
    try {
      await request.jwtVerify()
    } catch (err) {
      reply.status(401).send({ message: 'Unauthorized' })
    }
  })
})

declare module 'fastify' {
  interface FastifyInstance {
    authenticate: (request: FastifyRequest, reply: FastifyReply) => Promise<void>
  }
}
