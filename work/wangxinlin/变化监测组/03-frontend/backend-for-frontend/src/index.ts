import Fastify from 'fastify'
import cors from '@fastify/cors'
import jwtPlugin from './plugins/jwt.js'
import { authRoutes } from './handlers/auth.js'
import { landSupplyRoutes } from './handlers/land-supply.js'
import { config } from './config.js'

const fastify = Fastify({
  logger: {
    transport: {
      target: 'pino-pretty',
      options: { colorize: true },
    },
  },
})

async function main() {
  await fastify.register(cors, {
    origin: ['http://localhost:5173'],
    credentials: true,
  })

  await fastify.register(jwtPlugin)

  fastify.register(authRoutes, { prefix: '/api/auth' })
  fastify.register(landSupplyRoutes, { prefix: '/api/land-supplies' })

  fastify.get('/api/health', async () => ({ status: 'ok' }))

  try {
    await fastify.listen({ port: config.port, host: '0.0.0.0' })
    console.log(`BFF server listening on http://localhost:${config.port}`)
  } catch (err) {
    fastify.log.error(err)
    process.exit(1)
  }
}

main()
