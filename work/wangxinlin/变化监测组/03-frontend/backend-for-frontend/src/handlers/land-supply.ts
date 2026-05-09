import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify'
import { query } from '../database.js'

export async function landSupplyRoutes(fastify: FastifyInstance) {
  fastify.get('/', { preHandler: fastify.authenticate }, async (request: FastifyRequest<{ Querystring: { district?: string; page?: string; pageSize?: string } }>, reply: FastifyReply) => {
    const { district, page = '1', pageSize = '20' } = request.query
    const limit = Math.min(parseInt(pageSize, 10), 100)
    const offset = (Math.max(parseInt(page, 10), 1) - 1) * limit

    let whereClause = 'WHERE 1=1'
    const params: unknown[] = []

    if (district) {
      params.push(district)
      whereClause += ` AND district = $${params.length}`
    }

    const countResult = await query(`SELECT COUNT(*) as total FROM land_supplies ${whereClause}`, params)
    const total = parseInt(countResult.rows[0].total, 10)

    params.push(limit)
    params.push(offset)

    const result = await query(
      `SELECT id, resource_id, transfer_no, district, land_use_type,
              area_sqm, area_mu, plot_ratio, starting_price, transaction_price,
              transaction_date, estimated_date, transaction_stage, system_type,
              longitude, latitude, plot_name
       FROM land_supplies
       ${whereClause}
       ORDER BY created_at DESC
       LIMIT $${params.length - 1} OFFSET $${params.length}`,
      params
    )

    return {
      items: result.rows.map((row) => ({
        id: row.id,
        resourceId: row.resource_id,
        transferNo: row.transfer_no,
        district: row.district,
        landUseType: row.land_use_type,
        areaSqm: row.area_sqm,
        areaMu: row.area_mu,
        plotRatio: row.plot_ratio,
        startingPrice: row.starting_price,
        transactionPrice: row.transaction_price,
        transactionDate: row.transaction_date,
        estimatedDate: row.estimated_date,
        transactionStage: row.transaction_stage,
        systemType: row.system_type,
        longitude: row.longitude,
        latitude: row.latitude,
        plotName: row.plot_name,
      })),
      total,
    }
  })

  fastify.get('/:id', { preHandler: fastify.authenticate }, async (request: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const id = parseInt(request.params.id, 10)
    if (isNaN(id)) {
      return reply.status(400).send({ message: 'Invalid ID' })
    }

    const result = await query(
      `SELECT id, resource_id, transfer_no, district, land_use_type,
              area_sqm, area_mu, plot_ratio, starting_price, transaction_price,
              transaction_date, estimated_date, transaction_stage, system_type,
              longitude, latitude, plot_name
       FROM land_supplies WHERE id = $1`,
      [id]
    )

    if (result.rows.length === 0) {
      return reply.status(404).send({ message: 'Land supply not found' })
    }

    const row = result.rows[0]
    return {
      id: row.id,
      resourceId: row.resource_id,
      transferNo: row.transfer_no,
      district: row.district,
      landUseType: row.land_use_type,
      areaSqm: row.area_sqm,
      areaMu: row.area_mu,
      plotRatio: row.plot_ratio,
      startingPrice: row.starting_price,
      transactionPrice: row.transaction_price,
      transactionDate: row.transaction_date,
      estimatedDate: row.estimated_date,
      transactionStage: row.transaction_stage,
      systemType: row.system_type,
      longitude: row.longitude,
      latitude: row.latitude,
      plotName: row.plot_name,
    }
  })
}
